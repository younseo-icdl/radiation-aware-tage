#!/usr/bin/env python3
"""Bounded regression of native XOR injection and read-only CPU observations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = b'checksum: 2bf45f80b1c37877\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--binary', type=Path, default=ROOT/'build/checksum')
    p.add_argument('--native-reference', type=Path,
                   help='ordinary native checksum output from the finite gate')
    p.add_argument('--direct', action='store_true', help='Also test direct-query cost and cancellation')
    args = p.parse_args()
    if args.output.exists():
        p.error('output exists; choose a fresh directory')
    args.output = args.output.resolve()
    args.output.mkdir(parents=True)
    faults = args.output/'three.events'
    faults.write_text('# time_unit=ticks\n500001 R17\n7000001 W0:0\n13000001 W22:3\n')
    future = args.output/'future.events'
    future.write_text('# time_unit=ticks\n999999999999 R0\n')
    invalid = args.output/'duplicate.events'
    invalid.write_text('# time_unit=ticks\n500001 R0;R0\n')
    single = args.output/'single.events'
    single.write_text('# time_unit=ticks\n500001 R17\n')
    cases = [('light', []), ('trace', ['--diagnostics']),
             ('fault', ['--diagnostics', '--schedule', str(faults)]),
             ('censored', ['--diagnostics', '--schedule', str(future)]),
             ('duplicate', ['--schedule', str(invalid)])]
    if args.direct:
        cases += [('direct0', ['--direct', '--diagnostics']),
                  ('direct1', ['--direct', '--diagnostics', '--query-latency', '1']),
                  ('direct-fault', ['--direct', '--diagnostics', '--query-latency', '1',
                                    '--schedule', str(single)])]

    def run(item):
        name, extra = item
        out = args.output/name
        cmd = [sys.executable, str(ROOT/'tools/gem5.py'), 'run',
               '--tree', str(args.tree.resolve()), '--config',
               str(ROOT/'simulation/gem5/configs/native_study.py'),
               '--outdir', str(out), '--', '--binary', str(args.binary.resolve()),
               '--execute', '--max-ticks', '1000000000'] + extra
        row = {'case': name, 'status': 'FAIL', 'command': cmd}
        try:
            with (args.output/(name+'.log')).open('x') as log:
                result = subprocess.run(cmd, cwd=ROOT, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=120)
            row['returncode'] = result.returncode
            if name == 'duplicate':
                assert result.returncode != 0
                assert 'duplicate atomic site' in (args.output/(name+'.log')).read_text()
                row['status'] = 'PASS'
                return row
            assert result.returncode == 0
            assert (out/'program.stdout').read_bytes() == EXPECTED
            state = json.loads((out/'native.json').read_text())
            row['native'] = state
            assert state['missing_lookup_mapping'] == state['missing_retirement_mapping'] == 0
            assert state['faults_frozen']
            assert state['target_checker_stages'] == 0
            assert state['additional_lookup_hold'] == int(name in ('direct1', 'direct-fault'))
            assert state['additional_retirement_hold'] == 0
            assert state['periodic_service_clock'] is False
            if name == 'fault':
                assert state['applied_events'] == state['applied_flips'] == 3
                with (out/'events.csv').open() as f:
                    events = list(csv.DictReader(f))
                assert [int(e['requested_tick']) for e in events] == [500001, 7000001, 13000001]
                assert all(e['requested_tick'] == e['applied_tick'] for e in events)
            elif name == 'direct-fault':
                assert state['applied_events'] == state['applied_flips'] == 1
            else:
                assert state['applied_events'] == 0
            assert state['future_events_censored'] == int(name == 'censored')
            if name != 'light':
                with gzip.open(out/'committed.csv.gz', 'rt') as f:
                    count = 0
                    for x in csv.DictReader(f):
                        count += 1
                        assert None not in x and None not in x.values()
                        assert int(x['branch_id']) == count
                        assert int(x['retire_tick']) <= int(x['training_tick'])
                        assert x['sampling_phase'] == 'AFTER_QUERY_BEFORE_SPEC_APPEND'
                        if name.startswith('direct') and x['conditional'] == '1':
                            assert x['fold_invariant_distance'] == '0'
                assert count == state['committed_updates'] == state['retired_controls']
                row['trace_rows'] = count
            row['status'] = 'PASS'
        except (OSError, ValueError, AssertionError, subprocess.TimeoutExpired) as error:
            row['error'] = type(error).__name__ + ': ' + str(error)
        return row

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(run, cases))
    checks = []
    if all(x['status'] == 'PASS' for x in rows):
        states = {x['case']: x.get('native') for x in rows}
        fields = ['tick', 'semantic_base_fingerprint', 'raw_history_writes', 'lookups',
                  'committed_updates', 'retired_ops', 'retired_instructions',
                  'retired_controls', 'retired_pc_identity', 'lookup_identity']
        for name in ('trace', 'censored'):
            checks.append({'check': name+' transparency', 'status':
                'PASS' if all(states[name][f] == states['light'][f] for f in fields) else 'FAIL'})
        if args.direct:
            checks.append({'check': 'direct0 clean semantic and stream equivalence', 'status':
                'PASS' if all(states['direct0'][f] == states['light'][f] for f in fields) else 'FAIL'})
            checks.append({'check': 'direct1 actual charged query waits', 'status':
                'PASS' if states['direct1']['tick'] > states['light']['tick']
                and states['direct1']['query_wait_calls'] > 0
                and states['direct1']['delayed_requests'] > 0
                and states['direct1']['retired_pc_identity'] == states['light']['retired_pc_identity']
                else 'FAIL'})
        if args.native_reference:
            stats = dict(line.split()[:2] for line in
                         (args.native_reference/'stats.txt').read_text().splitlines()
                         if line.strip() and not line.startswith('-') and len(line.split()) >= 2)
            checks.append({'check': 'ordinary upstream native completion time', 'status':
                'PASS' if int(stats['simTicks']) == states['light']['tick'] else 'FAIL'})
    report = {'cases': rows, 'cross_checks': checks}
    (args.output/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    for x in rows + checks:
        print(json.dumps({k: v for k, v in x.items() if k not in ('native', 'command')}))
    return 0 if all(x['status'] == 'PASS' for x in rows + checks) else 1


if __name__ == '__main__':
    sys.exit(main())
