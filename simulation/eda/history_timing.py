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


def worst_path(text, view, analysis):
    match = re.search(r'^Path 1:\s+(MET|VIOLATED)\s+\(([+-]?\d+(?:\.\d+)?) (ns|ps)\) (Early|Late)\b',
                      text, re.MULTILINE)
    if not match or match[4] != analysis:
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
            or record['scope'] != 'B1A_HISTORY_DATAPATH'
            or record['CTS'] != 'FLOW_COMPLETE_CHECK_REPORTS'):
        raise ValueError('registered history requires a completed routed producer with CTS')
    utilization = record['die_utilization_percent']
    if not 65 <= utilization <= 75:
        raise ValueError('routed die utilization is outside 65–75%')
    synth = record['source_parent']
    period_ps = Decimal(str(synth['constraints']['clock_period_ns'])) * 1000
    paths = {key: worst_path((directory/'reports'/name).read_text(), view, analysis)
             for key, name, view, analysis in (
                 ('setup', 'setup_path.rpt', 'slowview', 'Late'),
                 ('hold', 'hold_path.rpt', 'fastview', 'Early'),
                 ('query_setup', 'query_setup.rpt', 'slowview', 'Late'),
             )}
    return {'producer': str(directory.resolve()), 'die_utilization_percent': utilization,
            'die_area_um2': record['die_area_um2'], 'source_commit': synth['source_commit'],
            'reference_period_ps': str(period_ps), 'paths': paths}


def matched_summary(recurrent, lease):
    cases = {'recurrent': routed_case(recurrent), 'lease4096': routed_case(lease)}
    values = list(cases.values())
    if any(values[0][key] != values[1][key] for key in ('reference_period_ps', 'source_commit')):
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('recurrent', 'lease', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--audit-no-undo', action='store_true')
    args = parser.parse_args()
    try:
        summary = matched_summary(args.recurrent, args.lease)
        with args.output.open('x') as out:
            json.dump(summary, out, indent=2)
            out.write('\n')
        if args.audit_no_undo:
            for name, route in (('recurrent', args.recurrent), ('lease4096', args.lease)):
                outdir = args.output.with_suffix('').with_name(args.output.stem+'-'+name)
                audit_no_undo(route, outdir)
    except (ValueError, OSError, KeyError) as error:
        parser.error(str(error))


def audit_no_undo(route, output):
    checkpoint = (route/'outputs/routed.inn').resolve(strict=True)
    output.mkdir()
    (output/'reports').mkdir()
    shutil.copy2(Path(__file__).with_name('innovus_history_modes.tcl'), output/'flow.tcl')
    (output/'site.tcl').write_text('set checkpoint '+tcl_word(checkpoint)+'\n')
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
    result['scope'] = 'query with all undo bits constrained to zero; remaining operands external'
    (output/'MODE_TIMING.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
