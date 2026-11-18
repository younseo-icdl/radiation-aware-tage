"""Summarize matched registered history STA without issuing CPU authorization."""
import argparse
from decimal import Decimal, ROUND_CEILING
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess

from .synthesize import tcl_word
from .implement import REGISTERED_HISTORY_SCOPES, retime_history_sdc


def worst_path(text, view, analysis):
    match = re.search(r'^Path 1:\s+(MET|VIOLATED)\s+\(([+-]?\d+(?:\.\d+)?) (ns|ps)\) '
                      r'(Early|Late|Hold Check|Setup Check)\b',
                      text, re.MULTILINE)
    kinds = {'Early': ('Early', 'Hold Check'), 'Late': ('Late', 'Setup Check')}
    if not match or match[4] not in kinds[analysis]:
        raise ValueError('no supported first-path slack for '+analysis+' analysis')
    fields = {}
    for field in ('View', 'Startpoint', 'Endpoint'):
        found = re.search(r'^\s*'+field+r':\s*(.+)$', text[match.end():], re.MULTILINE)
        if not found:
            raise ValueError('missing STA field: '+field)
        fields[field.lower()] = found.group(1).strip()
    if fields['view'] != view:
        raise ValueError('unexpected STA analysis view: '+fields['view'])
    slack = Decimal(match[2]) * (1000 if match[3] == 'ns' else 1)
    if (slack < 0 and match[1] != 'VIOLATED') or (slack > 0 and match[1] != 'MET'):
        raise ValueError('path status disagrees with signed slack')
    return {'slack_ps': str(slack), 'status': match[1], **fields}


def routed_case(directory):
    record = json.loads((directory/'PRODUCER.json').read_text())
    if (record['status'] != 'FLOW_COMPLETE_CHECK_REPORTS'
            or record['scope'] not in REGISTERED_HISTORY_SCOPES
            or record['CTS'] != 'FLOW_COMPLETE_CHECK_REPORTS'):
        raise ValueError('registered history requires a completed routed producer with CTS')
    utilization = record['die_utilization_percent']
    if not 65 <= utilization <= 75:
        raise ValueError('routed die utilization is outside 65–75%')
    synth = record['source_parent']
    route_period = record.get('route_clock_period_ns')
    if route_period is None:
        route_period = synth['constraints']['clock_period_ns']
    period_ps = Decimal(str(route_period)) * 1000
    paths = {key: worst_path((directory/'reports'/name).read_text(), view, analysis)
             for key, name, view, analysis in (
                 ('setup', 'setup_path.rpt', 'slowview', 'Late'),
                 ('hold', 'hold_path.rpt', 'fastview', 'Early'),
                 ('query_setup', 'query_setup.rpt', 'slowview', 'Late'),
             )}
    if record['scope'] == 'STAGED_HISTORY_RETURNED_ROWS':
        paths['provider_setup'] = worst_path(
            (directory/'reports/provider_to_state_setup.rpt').read_text(), 'slowview', 'Late')
    return {'producer': str(directory.resolve()), 'scope': record['scope'], 'die_utilization_percent': utilization,
            'die_area_um2': record['die_area_um2'], 'source_commit': synth['source_commit'],
            'reference_period_ps': str(period_ps), 'paths': paths}


def matched_summary(recurrent, lease):
    cases = {'recurrent': routed_case(recurrent), 'lease4096': routed_case(lease)}
    values = list(cases.values())
    if any(values[0][key] != values[1][key] for key in ('reference_period_ps', 'source_commit', 'scope')):
        raise ValueError('registered cases must share the source revision and clock target')
    period = Decimal(values[0]['reference_period_ps'])
    deficit = max(Decimal(0), *(-Decimal(case['paths'][key]['slack_ps'])
                                   for case in values for key in ('setup', 'query_setup')))
    return {
        'cases': cases,
        'common_history_period_estimate_ps': int((period + deficit).to_integral_value(rounding=ROUND_CEILING)),
        'hold_violation': any(case['paths']['hold']['status'] == 'VIOLATED' for case in values),
        'status': 'SUBSYSTEM_ESTIMATE_ONLY',
        'required_checks': ['recheck STA at proposed period', 'confirm DRC and connectivity',
                            'qualify provider and speculative operand arrival',
                            'verify update, undo, and lease publication timing'],
    }


def row_arrival_constraints(arrival_ps, target_arrival_ps=None):
    # Change only the late constraint. The original early input delay
    # remains in the hold analysis.
    constraints = ''
    for time, ports in (
        (arrival_ps, 'row_tag_i* row_counter_i* bimodal_prediction_i'),
        (target_arrival_ps, 'taken_target_valid_i'),
    ):
        if time is not None:
            if time <= 0:
                raise ValueError('late arrival must be positive')
            ns = Decimal(time)/1000
            constraints += (f'\nset_input_delay -clock [get_clocks history_clk] -max {ns:f} '
                            f'[get_ports {{{ports}}}]\n')
    return constraints


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('recurrent', 'lease', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--audit-no-undo', action='store_true')
    parser.add_argument('--recheck-period-ps', type=int,
                        help='Recheck both routed checkpoints at a specified common clock')
    parser.add_argument('--recheck-cppr', choices=('none', 'both'),
                        help='Set the same CPPR policy on both rechecked checkpoints')
    parser.add_argument('--row-arrival-ps', type=int,
                        help='Recheck both staged checkpoints at an explicitly bounded latest row arrival')
    parser.add_argument('--target-arrival-ps', type=int,
                        help='Bound the external taken-target-valid arrival for staged feedback')
    args = parser.parse_args()
    try:
        if args.recheck_period_ps is not None and args.recheck_period_ps <= 0:
            raise ValueError('recheck clock period must be positive')
        if args.recheck_cppr is not None and args.recheck_period_ps is None:
            raise ValueError('a CPPR override requires an explicit recheck period')
        summary = matched_summary(args.recurrent, args.lease)
        arrivals = [x for x in (args.row_arrival_ps, args.target_arrival_ps) if x is not None]
        if arrivals:
            if (args.recheck_period_ps is None or
                    summary['cases']['recurrent']['scope'] != 'STAGED_HISTORY_RETURNED_ROWS' or
                    any(not 0 < x < args.recheck_period_ps for x in arrivals)):
                raise ValueError('operand arrival requires a staged checkpoint and a larger recheck period')
        with args.output.open('x') as out:
            json.dump(summary, out, indent=2)
            out.write('\n')
        if args.audit_no_undo or args.recheck_period_ps is not None:
            for name, route in (('recurrent', args.recurrent), ('lease4096', args.lease)):
                outdir = args.output.with_suffix('').with_name(args.output.stem+'-'+name)
                audit_no_undo(route, outdir, args.recheck_period_ps, args.recheck_cppr,
                              args.row_arrival_ps, args.target_arrival_ps)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))


def audit_no_undo(route, output, period_ps=None, cppr=None, row_arrival_ps=None, target_arrival_ps=None):
    checkpoint = (route/'outputs/routed.inn').resolve(strict=True)
    pipeline = json.loads((route/'PRODUCER.json').read_text())['scope'] == 'STAGED_HISTORY_RETURNED_ROWS'
    output.mkdir()
    (output/'reports').mkdir()
    shutil.copy2(Path(__file__).with_name('innovus_history_modes.tcl'), output/'flow.tcl')
    (output/'site.tcl').write_text('set checkpoint '+tcl_word(checkpoint)+'\n'
                                 f'set retimed {int(period_ps is not None)}\n'
                                 f'set pipeline {int(pipeline)}\n'
                                 'set cppr '+tcl_word(cppr or '')+'\n')
    if period_ps is not None:
        (output/'inputs').mkdir()
        original = (route/'inputs/mapped.sdc').read_text()
        constraints = retime_history_sdc(original, Decimal(period_ps)/1000)
        (output/'inputs/recheck.sdc').write_text(
            constraints + row_arrival_constraints(row_arrival_ps, target_arrival_ps))
    cmd = ['innovus', '-stylus', '-no_gui', '-files', 'flow.tcl', '-log', 'innovus.log']
    log = output/'console.log'
    with log.open('x') as stream:
        proc = subprocess.run(['timeout', '-k', '10', '1200', 'csh', '-c',
                               'exec '+shlex.join(cmd)], cwd=output, stdout=stream,
                              stderr=subprocess.STDOUT)
    if proc.returncode or 'PASS_TAGE_HISTORY_MODE_REPORTS' not in log.read_text(errors='replace'):
        raise ValueError(f'query mode audit failed; reports retained in {output}')
    result = {mode: worst_path((output/'reports'/f'query_{mode}.rpt').read_text(), 'slowview', 'Late')
              for mode in ('unrestricted', 'no_undo')}
    if period_ps is not None:
        result['rechecked_period_ps'] = period_ps
        result['cppr'] = (output/'reports/cppr.txt').read_text().strip()
        result['setup'] = worst_path((output/'reports/rechecked_setup.rpt').read_text(), 'slowview', 'Late')
        result['hold'] = worst_path((output/'reports/rechecked_hold.rpt').read_text(), 'fastview', 'Early')
        if pipeline:
            result['late_row_arrival_override_ps'] = row_arrival_ps
            result['late_target_arrival_override_ps'] = target_arrival_ps
            result['address_launch_setup'] = worst_path(
                (output/'reports/address_launch_setup.rpt').read_text(), 'slowview', 'Late')
            result['provider_setup'] = worst_path(
                (output/'reports/provider_to_state_setup.rpt').read_text(), 'slowview', 'Late')
    result['scope'] = 'query with all undo bits constrained to zero; remaining operands external'
    (output/'MODE_TIMING.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
