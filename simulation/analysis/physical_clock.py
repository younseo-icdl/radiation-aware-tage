"""Bind a native comparison clock to its routed history-block timing evidence."""
import argparse
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path

from simulation.eda.history_timing import retime_history_sdc, row_arrival_constraints, worst_path
from simulation.eda.synthesize import tcl_word

# Order is lease appends, SECDED, committed refill, TMR.
MODE = {
    'unprotected': (0, 0, 0, 0), 'rebuild': (4096, 0, 0, 0),
    'ecc-halt': (0, 1, 0, 0), 'ecc-refill': (0, 1, 1, 0),
    'tmr': (0, 0, 0, 1),
}
PATHS = {
    'setup': ('rechecked_setup.rpt', 'slowview', 'Late'),
    'hold': ('rechecked_hold.rpt', 'fastview', 'Early'),
    'address_launch_setup': ('address_launch_setup.rpt', 'slowview', 'Late'),
    'provider_setup': ('provider_to_state_setup.rpt', 'slowview', 'Late'),
    'target_setup': ('target_to_state_setup.rpt', 'slowview', 'Late'),
}


def read(path):
    return json.loads(path.read_text())


def sha256(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def arm_evidence(mode, route, sta, period, arrival, target):
    metadata = read(route / 'PRODUCER.json')
    synth = metadata['source_parent']
    config = synth['constraints']
    options = tuple(config.get(key, 0) for key in ('lease_period', 'secded', 'ecc_refill', 'tmr'))
    complete = 'FLOW_COMPLETE_CHECK_REPORTS'
    if (metadata['status'] != complete or metadata['CTS'] != complete or synth['status'] != 'PASS'
            or metadata['scope'] != 'STAGED_HISTORY_RETURNED_ROWS'
            or options != MODE[mode] or config['pipeline'] != 1 or config['direct_mask'] != 0
            or config['lease_service_cycles'] != 2 or config['publish_mask'] != (127 if mode == 'rebuild' else 0)
            or not 65 <= metadata['die_utilization_percent'] <= 75):
        raise ValueError(f'{mode}: routed history mode or utilization differs from the CPU contract')
    geometry = route / 'reports'
    if ('No DRC violations were found' not in (geometry / 'internal_drc.rpt').read_text()
            or any('Found no problems or warnings.' not in (geometry / f'{name}.rpt').read_text()
                   for name in ('connectivity', 'pg_connectivity'))):
        raise ValueError(f'{mode}: routed geometry failed')
    checkpoint = (route / 'outputs/routed.inn').resolve(strict=True)
    if f'set checkpoint {tcl_word(checkpoint)}' not in (sta / 'site.tcl').read_text().splitlines():
        raise ValueError(f'{mode}: STA did not load this routed checkpoint')
    timing = read(sta / 'MODE_TIMING.json')
    if (timing['rechecked_period_ps'], timing['late_row_arrival_override_ps'],
            timing['late_target_arrival_override_ps'], timing['cppr']) != (period, arrival, target, 'both'):
        raise ValueError(f'{mode}: STA conditions differ from the matched clock contract')
    reports = sta / 'reports'
    sdc = sta / 'inputs/recheck.sdc'
    configured = retime_history_sdc((route / 'inputs/mapped.sdc').read_text(), Decimal(period) / 1000)
    if (sdc.read_text() != configured + row_arrival_constraints(arrival, target)
            or (reports / 'cppr.txt').read_text().strip() != 'both'):
        raise ValueError(f'{mode}: applied STA constraints do not match the declared contract')
    hashes = {}
    for key, (filename, view, analysis) in PATHS.items():
        path = reports / filename
        observed = worst_path(path.read_text(), view, analysis)
        slack = Decimal(observed['slack_ps'])
        if observed != timing[key] or not slack.is_finite() or slack < 0:
            raise ValueError(f'{mode}: {key} is violated or differs from the STA summary')
        hashes[key] = sha256(path)
    return dict(die_utilization_percent=metadata['die_utilization_percent'],
                postroute_verilog_sha256=sha256(route / 'outputs/postroute.v'),
                sta_reports_sha256=hashes, producer_sha256=sha256(route / 'PRODUCER.json'),
                sta_summary_sha256=sha256(sta / 'MODE_TIMING.json'), sta_constraints_sha256=sha256(sdc))


def qualified_clock(root):
    clock = read(root / 'COMMON_CLOCK.json')
    routes = read(root / 'SELECTED_ROUTES.json')['paths']
    period, arrival, target = (clock[key] for key in ('period_ps', 'row_arrival_ps', 'target_arrival_ps'))
    if (type(period) is not int or not 0 < arrival < target < period
            or not math.isclose(clock['clock_mhz'], 1e6 / period)
            or set(routes) != set(MODE) or set(clock['timing']) != set(MODE)
            or clock['tested_periods_ps'][-1] != period):
        raise ValueError('no complete matched common physical clock')
    batch = root / f'recheck-{period}ps'
    evidence = {}
    for mode, path in routes.items():
        sta = batch / mode
        if read(sta / 'MODE_TIMING.json') != clock['timing'][mode]:
            raise ValueError(f'{mode}: common clock summary disagrees with the arm report')
        evidence[mode] = arm_evidence(mode, Path(path), sta, period, arrival, target)
    return dict(scope='routed history subsystem and external row/target arrival contract',
                clock_period_ticks=period, ticks_per_second=10**12, clock_mhz=clock['clock_mhz'],
                row_arrival_ps=arrival, target_arrival_ps=target, query_latency_cycles=2,
                initiation_interval_cycles=1, training_admission_per_cycle=1, lease_service_cycles=2,
                common_clock_sha256=sha256(root / 'COMMON_CLOCK.json'),
                selected_routes_sha256=sha256(root / 'SELECTED_ROUTES.json'), arms=evidence)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('physical_evidence', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(qualified_clock(args.physical_evidence), indent=2))
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
