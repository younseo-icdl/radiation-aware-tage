#!/usr/bin/env python3
"""Bounded regression of native XOR injection and read-only CPU observations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = b'checksum: 2bf45f80b1c37877\n'
FRONTEND_CONTROL_OUTPUT = b'frontend-control: PASS\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--binary', type=Path, default=ROOT/'build/checksum')
    p.add_argument('--config', type=Path, default=ROOT/'simulation/gem5/configs/native_study.py')
    p.add_argument('--native-reference', type=Path,
                   help='ordinary native checksum output from the finite gate')
    p.add_argument('--direct', action='store_true', help='Also test direct-query cost and cancellation')
    p.add_argument('--integrated', action='store_true', help='Also test hybrid/lease, actual BPU observations, and tape coverage')
    p.add_argument('--query-interval', action='store_true',
                   help='Exercise matched conditional-query pacing and observe issued queries')
    p.add_argument('--query-pipeline', action='store_true',
                   help='Check registered hash operands in both arms, including an inter-stage fault')
    p.add_argument('--single-training-port', action='store_true',
                   help='Check staged conditional training-port retirement reservations')
    p.add_argument('--frontend-control', type=Path,
                   help='Also check the freestanding x86 microcode branch regression')
    p.add_argument('--cycle-ticks', type=int, default=500,
                   help='CPU period in 1 ps units for the bounded native gate')
    args = p.parse_args()
    if args.cycle_ticks < 2:
        p.error('cycle period must leave an interior tick for directed faults')
    if args.single_training_port and not args.query_pipeline:
        p.error('--single-training-port requires --query-pipeline')
    named_files = {'gem5': args.tree/'build/X86/gem5.opt',
                   'config': args.config, 'baseline': args.config.with_name('baseline.py'),
                   'checksum': args.binary}
    if args.frontend_control:
        if not args.query_pipeline:
            p.error('--frontend-control requires --query-pipeline')
        named_files['frontend_control'] = args.frontend_control
    provenance = {}
    for name, path in named_files.items():
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for chunk in iter(lambda: source.read(1024*1024), b''):
                digest.update(chunk)
        provenance[name] = digest.hexdigest()
    capture_end = 80_000 * args.cycle_ticks
    capture = ['--activity-end-tick', str(capture_end)]
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
    age = args.output/'age.events'
    age.write_text('# time_unit=ticks\n500001 L:AGE:2\n')
    live_fold = args.output/'live-fold.events'
    live_fold.write_text('# time_unit=ticks\n500001 W3:0\n')
    dead_fold = args.output/'dead-fold.events'
    dead_fold.write_text('# time_unit=ticks\n500001 W0:0\n')
    short_tape = args.output/'short.events'
    short_tape.write_text('# time_unit=ticks horizon=500\n')
    cases = [('light', []), ('trace', ['--diagnostics']),
             ('fault', ['--diagnostics', '--schedule', str(faults)]),
             ('censored', ['--diagnostics', '--schedule', str(future)]),
             ('duplicate', ['--schedule', str(invalid)])]
    if args.direct:
        cases += [('direct0', ['--direct', '--diagnostics']),
                  ('direct1', ['--direct', '--diagnostics', '--query-latency', '1']),
                  ('direct-fault', ['--direct', '--diagnostics', '--query-latency', '1',
                                    '--schedule', str(single)])]
    if args.integrated:
        hybrid = ['--direct-bank-mask','5','--diagnostics']
        lease = ['--lease-period','64','--lease-service-cycles','2','--diagnostics']
        cases += [('hybrid',hybrid), ('hybrid-fault',hybrid+['--schedule',str(single)]),
                  ('hybrid-live-fold',hybrid+['--schedule',str(live_fold)]),
                  ('hybrid-dead-fold',hybrid+['--schedule',str(dead_fold)]),
                  ('lease',lease), ('lease-fault',lease+['--schedule',str(faults)]),
                  ('lease-age',lease+['--schedule',str(age)]),
                  ('short-tape',['--diagnostics','--schedule',str(short_tape)])]
    intervals = {}
    pipelines = {}
    pipeline_faults = {}
    frontend_cases = {}
    if args.frontend_control:
        frontend_cases = {'frontend-control-native': [], 'frontend-control-staged': ['--query-pipeline']}
        if args.single_training_port:
            frontend_cases['frontend-control-staged'].append('--single-training-port')
        cases.extend(frontend_cases.items())
    if args.query_pipeline:
        for model in ('native', 'lease4096'):
            name = f'pipeline-{model}'
            mode = ['--lease-period', '4096'] if model == 'lease4096' else []
            pipelines[name] = (model, ['--query-pipeline'] + mode)
            cases.append((name, pipelines[name][1]+capture))
            if args.single_training_port:
                port_case = name+'-training-port'
                port_args = pipelines[name][1]+['--single-training-port']
                pipelines[port_case] = (model, port_args)
                cases.append((port_case, port_args+capture))
    if args.query_interval:
        for model in ('native', 'lease4096'):
            mode = ['--lease-period', '4096'] if model == 'lease4096' else []
            for cycles in (0, 2, 4):
                name = f'interval-{model}-{cycles}'
                intervals[name] = (model, cycles)
                pace = ['--query-ii-cycles', str(cycles)] if cycles else []
                cases.append((name, mode + pace + capture))
            name = f'interval-{model}-4-fault'
            intervals[name] = (model, 4)
            cases.append((name, mode + ['--query-ii-cycles', '4', '--schedule', str(faults)]))

    def run(item):
        name, extra = item
        frontend_case = name in frontend_cases
        interval_fault = name in intervals and name.endswith('-fault')
        pipeline_model = pipelines[name][0] if name in pipelines else None
        out = args.output/name
        binary = args.frontend_control if frontend_case else args.binary
        cmd = [sys.executable, str(ROOT/'tools/gem5.py'), 'run',
               '--tree', str(args.tree.resolve()), '--config',
               str(args.config.resolve()),
               '--outdir', str(out), '--', '--binary', str(binary.resolve()),
               '--cycle-ticks', str(args.cycle_ticks),
               '--execute', '--max-ticks', str(2_000_000 * args.cycle_ticks)] + extra
        row = {'case': name, 'status': 'FAIL', 'command': cmd}
        try:
            with (args.output/(name+'.log')).open('x') as log:
                result = subprocess.run(cmd, cwd=ROOT, stdout=log,
                                        stderr=subprocess.STDOUT, timeout=120)
            row['returncode'] = result.returncode
            if name in ('duplicate','hybrid-dead-fold'):
                assert result.returncode != 0
                message = 'duplicate atomic site' if name=='duplicate' else 'no consumed stored-fold target'
                assert message in (args.output/(name+'.log')).read_text()
                row['status'] = 'PASS'
                return row
            assert result.returncode == 0
            expected = FRONTEND_CONTROL_OUTPUT if frontend_case else EXPECTED
            assert (out/'program.stdout').read_bytes() == expected
            state = json.loads((out/'native.json').read_text())
            row['native'] = state
            if frontend_case:
                termination = json.loads((out/'termination.json').read_text())
                stats = dict(line.split()[:2] for line in (out/'stats.txt').read_text().splitlines()
                             if len(line.split()) >= 2)
                prefix = 'system.cpu.branchPred.lookups_0::'
                assert termination['status'] == 'PASS' and state['faults_frozen']
                assert int(stats[prefix+'NoBranch']) > 0 and int(stats[prefix+'DirectCond']) > 0
                if name == 'frontend-control-staged':
                    assert state['staged_query_responses'] == int(stats[prefix+'DirectCond'])
                row['status'] = 'PASS'
                return row
            assert state['missing_lookup_mapping'] == state['missing_retirement_mapping'] == 0
            if args.integrated:
                assert state['missing_bpu_mapping'] == state['missing_bpu_prediction_mapping'] == 0
                assert state['maximum_all_live_history_owners'] > 0
                assert state['schedule_exhausted_before_exit'] == (name=='short-tape')
            assert state['faults_frozen']
            assert state['target_checker_stages'] == 0
            assert state['additional_lookup_hold'] == int(name in ('direct1', 'direct-fault'))
            assert state['additional_retirement_hold'] == 0
            assert state['periodic_service_clock'] is False
            if name in pipeline_faults:
                tick, after_capture, clean_hash = pipeline_faults[name]
                assert state['applied_events'] == state['applied_flips'] == 1
                with (out/'events.csv').open() as f:
                    event, = csv.DictReader(f)
                assert int(event['requested_tick']) == int(event['applied_tick']) == tick
                assert state['staged_responses_after_fault'] == int(after_capture)
                assert state['staged_responses_with_changed_hash'] == int(after_capture)
                assert (state['first_staged_hash_identity'] == clean_hash) == after_capture
            elif name in ('fault','lease-fault') or interval_fault:
                assert state['applied_events'] == state['applied_flips'] == 3
                with (out/'events.csv').open() as f:
                    events = list(csv.DictReader(f))
                assert [int(e['requested_tick']) for e in events] == [500001, 7000001, 13000001]
                assert all(e['requested_tick'] == e['applied_tick'] for e in events)
            elif name in ('direct-fault','hybrid-fault','hybrid-live-fold','lease-age'):
                assert state['applied_events'] == state['applied_flips'] == 1
            else:
                assert state['applied_events'] == 0
            assert state['future_events_censored'] == int(name == 'censored')
            if pipeline_model:
                issue = state['first_staged_issue_tick']
                capture_tick = state['first_staged_capture_tick']
                assert issue > 0
                assert capture_tick - issue == state['first_staged_response_tick'] - capture_tick == args.cycle_ticks
                assert state['staged_query_hash_cycles'] == state['staged_query_row_cycles'] == 1
                assert state['maximum_conditional_lookups_per_tick'] == 1
                assert state['staged_query_responses'] > 0 and state['canceled_query_requests'] > 0
                assert state['staged_query_responses'] <= state['staged_query_captures'] <= state['delayed_requests']
                accounted = (state['staged_query_responses'] + state['staged_query_retries']
                             + state['canceled_query_requests'])
                assert state['delayed_requests'] - accounted in (0, 1)
                assert (state['lease_publications'] > 0) == (pipeline_model == 'lease4096')
                if '--single-training-port' in extra:
                    assert state['conditional_training_port_capacity'] == 1
                    untrained = state['conditional_training_port_reservations'] - state['conditional_updates']
                    assert 0 <= untrained <= state['all_live_history_owners_at_exit']
                if name not in pipeline_faults:
                    with (out/'history_activity.csv').open() as f:
                        assert next(f).strip() == f'# capture_end_tick={capture_end}'
                        activity = list(csv.DictReader(f))
                    query_ticks = [int(x['tick']) for x in activity
                                   if x['operation'] in ('query','hash_capture')]
                    assert query_ticks[0] == capture_tick
                    assert min(b-a for a,b in zip(query_ticks,query_ticks[1:])) >= args.cycle_ticks
                    if any(x['operation']=='query_request' for x in activity):
                        review = out/'STAGED_ACTIVITY.json'
                        subprocess.run([sys.executable, '-m', 'simulation.analysis.history_activity',
                                        str(out/'history_activity.csv'), '--output', str(review),
                                        '--period-ticks', str(args.cycle_ticks)],
                                       cwd=ROOT, check=True, capture_output=True)
                        result = json.loads(review.read_text())
                        assert 'staged_queries' in result
                        assert result['peak_per_tick']['hash_capture'] == 1
                        assert result['peak_per_tick']['row_response'] == 1
            if name in intervals:
                model, cycles = intervals[name]
                assert state.get('conditional_query_interval_cycles', 0) == cycles
                assert (state.get('query_interval_wait_calls', 0) > 0) == (cycles == 4)
                if interval_fault:
                    assert (state['lease_publications'] > 0) == (model == 'lease4096')
                else:
                    with (out/'history_activity.csv').open() as f:
                        assert next(f).strip() == f'# capture_end_tick={capture_end}'
                        activity = list(csv.DictReader(f))
                    queries = [int(x['tick']) for x in activity if x['operation'] == 'query']
                    gap = min(b-a for a, b in zip(queries, queries[1:]))
                    row['minimum_conditional_query_gap_ticks'] = gap
                    assert gap >= args.cycle_ticks * cycles
                    assert any(x['operation'] == 'publish' for x in activity) == (model == 'lease4096')
            if args.integrated:
                with (out/'events.csv').open() as f:
                    for event in csv.DictReader(f):
                        before = list(map(int,event['bit_values_before'].split(';')))
                        after = list(map(int,event['bit_values_after'].split(';')))
                        assert len(before)==len(after)==int(event['multiplicity'])
                        assert all((a^b)==1 for a,b in zip(before,after))
                if name.startswith('lease') or pipeline_model == 'lease4096':
                    assert state['lease_publications'] > 0
                    assert state['lease_frontend_wait_calls'] > 0
                    assert state['lease_service_wait_calls'] > 0
                    pending = None; publications = 0
                    with (out/'lease_events.csv').open() as f:
                        for event in csv.DictReader(f):
                            assert event['live_owners']=='0'
                            if event['event']=='start':
                                assert pending is None
                                pending=int(event['ready_tick'])
                                assert pending-int(event['tick'])==2*args.cycle_ticks
                            else:
                                assert event['event']=='publish' and pending==int(event['tick'])
                                publications+=1;pending=None
                    assert publications==state['lease_publications']
                    assert (pending is not None)==state['lease_completion_censored_at_exit']
            if name != 'light' and name not in intervals and not pipeline_model:
                with gzip.open(out/'committed.csv.gz', 'rt') as f:
                    count = 0; bpu_misses = 0
                    for x in csv.DictReader(f):
                        count += 1
                        assert None not in x and None not in x.values()
                        assert int(x['branch_id']) == count
                        assert int(x['retire_tick']) <= int(x['training_tick'])
                        assert x['sampling_phase'] == 'AFTER_QUERY_BEFORE_SPEC_APPEND'
                        if name.startswith('direct') and x['conditional'] == '1':
                            assert x['fold_invariant_distance'] == '0'
                        if args.integrated:
                            bpu_misses += int(x['bpu_mispredicted'])
                            assert int(x['bpu_predicted_target']) >= 0
                            if x['bpu_mispredicted']=='0':
                                assert x['bpu_predicted_target']==x['target']
                assert count == state['committed_updates'] == state['retired_controls']
                row['trace_rows'] = count
                if args.integrated:
                    stats = dict(line.split()[:2] for line in (out/'stats.txt').read_text().splitlines()
                                 if line.strip() and not line.startswith('-') and len(line.split())>=2)
                    assert bpu_misses == int(stats['system.cpu.branchPred.mispredicted_0::total'])
            row['status'] = 'PASS'
        except (OSError, ValueError, AssertionError, subprocess.SubprocessError) as error:
            row['error'] = type(error).__name__ + ': ' + str(error)
            if isinstance(error, subprocess.CalledProcessError) and error.stderr:
                row['error'] += ': ' + error.stderr.decode(errors='replace').strip()
        return row

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(run, cases))
        staged_faults = []
        for row in rows:
            name = row['case']
            if name not in pipelines or row['status'] != 'PASS':
                continue
            if '--single-training-port' in pipelines[name][1]:
                continue
            clean = row['native']
            for phase, edge in (('pre-latch','issue'), ('interstage','capture')):
                tick = clean[f'first_staged_{edge}_tick'] + 1
                fault_case = f'{name}-{phase}'
                fault = args.output/(fault_case+'.events')
                fault.write_text(f'# time_unit=ticks\n{tick} W0:0\n')
                pipelines[fault_case] = pipelines[name]
                pipeline_faults[fault_case] = (tick, edge=='capture', clean['first_staged_hash_identity'])
                staged_faults.append((fault_case, pipelines[name][1]+['--schedule',str(fault)]))
        rows += list(pool.map(run, staged_faults))
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
        if args.integrated:
            checks.append({'check':'hybrid clean exact stream/state/time equivalence','status':
                'PASS' if all(states['hybrid'][f]==states['light'][f] for f in fields) else 'FAIL'})
        if args.query_interval:
            for model in ('native', 'lease4096'):
                disabled = states[f'interval-{model}-0']
                low = states[f'interval-{model}-2']
                high = states[f'interval-{model}-4']
                checks.append({'check': f'{model} matched query interval', 'status': 'PASS'
                    if all(low[f] == disabled[f] for f in fields)
                    and high['tick'] > disabled['tick']
                    and high['retired_pc_identity'] == disabled['retired_pc_identity'] else 'FAIL'})
        if args.query_pipeline:
            for name in pipelines:
                assert name in states
                checks.append({'check': name+' preserves architectural stream', 'status': 'PASS'
                               if states[name]['retired_pc_identity']==states['light']['retired_pc_identity']
                               else 'FAIL'})
        if frontend_cases:
            checks.append({'check': 'internal microcode branch preserves architectural stream',
                           'status': 'PASS' if
                           states['frontend-control-native']['retired_pc_identity'] ==
                           states['frontend-control-staged']['retired_pc_identity'] else 'FAIL'})
        if args.native_reference:
            stats = dict(line.split()[:2] for line in
                         (args.native_reference/'stats.txt').read_text().splitlines()
                         if line.strip() and not line.startswith('-') and len(line.split()) >= 2)
            checks.append({'check': 'ordinary upstream native completion time', 'status':
                'PASS' if int(stats['simTicks']) == states['light']['tick'] else 'FAIL'})
    report = {'cycle_ticks': args.cycle_ticks, 'sha256': provenance,
              'cases': rows, 'cross_checks': checks}
    (args.output/'audit.json').write_text(json.dumps(report, indent=2)+'\n')
    for x in rows + checks:
        print(json.dumps({k: v for k, v in x.items() if k not in ('native', 'command')}))
    return 0 if all(x['status'] == 'PASS' for x in rows + checks) else 1


if __name__ == '__main__':
    sys.exit(main())
