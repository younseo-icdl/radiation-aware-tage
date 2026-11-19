"""Native TAGE and explicitly costed direct-query comparisons.

There is no common finite controller. The default native path has no added
latency; --query-latency explicitly charges a conditional-query admission wait.
This is not a pristine certification campaign or physical timing qualification.
"""
import argparse
import json
from pathlib import Path
import sys
import m5
from m5.objects import Root, NativeTAGE, NativeTAGEBase
sys.path.insert(0, str(Path(__file__).resolve().parent))
from baseline import create_system


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--schedule', type=Path)
    parser.add_argument('--diagnostics', action='store_true')
    parser.add_argument('--activity-end-tick', type=int, default=0,
                        help='Capture clean history operations before this absolute tick')
    parser.add_argument('--capture-staged-rows', action='store_true',
                        help='Capture the actual returned tagged/base rows and BPU target validity')
    parser.add_argument('--direct', action='store_true', help='Direct own-history query folds')
    parser.add_argument('--direct-bank-mask', type=lambda s:int(s,0), default=0)
    parser.add_argument('--history-protection', choices=('none', 'ecc_halt', 'ecc_refill', 'tmr'), default='none')
    parser.add_argument('--lease-period', type=int, default=0,
                        help='Actual raw appends (including speculation/unconditional) per rebase')
    parser.add_argument('--lease-service-cycles', type=int, default=2,
                        help='Charged quiescent service, development assumption until qualified')
    parser.add_argument('--cycle-ticks', type=int, default=500,
                        help='CPU period in default 1ps ticks; does not rescale the fault tape')
    parser.add_argument('--max-restore-owners', type=int, default=512)
    parser.add_argument('--query-latency', type=int, default=0,
                        help='Additional conditional-query CPU cycles, explicitly modeled')
    parser.add_argument('--query-ii-cycles', type=int, default=0,
                        help='Optional minimum gap between conditional query issues')
    parser.add_argument('--query-pipeline', action='store_true',
                        help='Register indices/tags before reading rows on a subsequent CPU cycle')
    parser.add_argument('--single-training-port', action='store_true',
                        help='Charge one conditional branch retirement reservation per CPU cycle')
    parser.add_argument('--max-ticks', type=int, default=2000000000000)
    parser.add_argument('--seed', type=int, default=548)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--execute', action='store_true')
    mode.add_argument('--initialize-only', action='store_true')
    args = parser.parse_args()
    if not args.binary.is_file() or (args.input and not args.input.is_file()):
        parser.error('binary or input does not exist')
    if args.schedule and not args.schedule.is_file():
        parser.error('schedule does not exist')
    if args.activity_end_tick < 0 or (args.activity_end_tick and (args.schedule or args.initialize_only)):
        parser.error('history activity capture requires a positive bound and an executed clean run')
    if args.max_ticks <= 0:
        parser.error('max-ticks must be positive')
    if not 0 <= args.query_latency <= 32:
        parser.error('query-latency must be 0..32')
    if not 0 <= args.query_ii_cycles <= 32 or (args.query_ii_cycles and args.query_latency):
        parser.error('query II must be 0..32 and cannot be combined with delayed query latency')
    if (not 0 <= args.direct_bank_mask < 128 or not 0 <= args.lease_period <= 65535
            or args.lease_service_cycles <= 0 or args.cycle_ticks <= 0 or args.max_restore_owners <= 0):
        parser.error('invalid mask, lease, clock, or owner capacity')
    if args.lease_period and (args.direct or args.direct_bank_mask or args.query_latency):
        parser.error('combined lease/direct/delayed policies are not admitted')
    if args.query_pipeline and (args.direct or args.direct_bank_mask or args.query_latency
                                or args.query_ii_cycles or args.diagnostics):
        parser.error('staged hashing requires recurrent operands without legacy pacing or commit diagnostics')
    if args.single_training_port and not args.query_pipeline:
        parser.error('single-port training requires the registered query mode')
    if args.history_protection != 'none' and (
            not args.query_pipeline or args.lease_period or args.activity_end_tick):
        parser.error('native protection requires the staged recurrent query path')
    if args.history_protection == 'ecc_refill' and not args.single_training_port:
        parser.error('committed refill requires native retirement admission')
    if args.capture_staged_rows and (not args.query_pipeline or not args.activity_end_tick):
        parser.error('returned-row capture requires bounded staged history activity')
    output = Path(m5.options.outdir).resolve()
    activity = dict(history_activity_file=str(output/'history_activity.csv'),
                    history_activity_end_tick=args.activity_end_tick) if args.activity_end_tick else {}
    base = NativeTAGEBase(minHist=5, maxHist=130, takenOnlyHistory=False,
        history_protection=args.history_protection,
        direct_queries=args.direct,
        direct_bank_mask=args.direct_bank_mask, lease_period=args.lease_period,
        lease_latency_ticks=args.lease_service_cycles*args.cycle_ticks,
        lease_log_file=str(output/'lease_events.csv') if args.lease_period else '',
        speculativeHistUpdate=True,
        schedule_file=str(args.schedule.resolve()) if args.schedule else '',
        event_file=str(output/'events.csv'), summary_file=str(output/'native.json'),
        manifest_file=str(output/'logical_manifest.json'),
        origin_file=str(output/'raw_origins.csv') if args.diagnostics else '', **activity)
    issue_interval = dict(query_ii_cycles=args.query_ii_cycles) if args.query_ii_cycles else {}
    pipeline = dict(query_pipeline=True) if args.query_pipeline else {}
    training = dict(single_training_port=True) if args.single_training_port else {}
    rows = dict(row_activity_file=str(output/'staged_rows.csv')) if args.capture_staged_rows else {}
    predictor = NativeTAGE(tage=base,
        query_latency=args.query_latency, cycle_ticks=args.cycle_ticks,
        max_restore_owners=args.max_restore_owners,
        commit_trace_file=str(output/'committed.csv.gz') if args.diagnostics else '',
        **issue_interval, **pipeline, **training, **rows)
    system = create_system(args, output, predictor)
    root = Root(full_system=False, system=system)
    m5.core.seedRandom(args.seed)
    m5.instantiate()
    if args.initialize_only:
        assert m5.curTick() == 0
        print('PASS_TICK0_NO_CPU')
        return root
    event = m5.simulate(args.max_ticks)
    base.dumpResearch()  # Freeze at actual architectural exit, without helper advance.
    m5.stats.dump()
    success = event.getCause() == 'exiting with last active thread context' and event.getCode() == 0
    detected_stop = (args.history_protection == 'ecc_halt' and
                     event.getCause() == 'native history SECDED detected uncorrectable error')
    (output/'termination.json').write_text(json.dumps({
        'status': 'PASS' if success else 'DETECTED_STOP' if detected_stop else 'FAIL',
        'program_exit_tick': m5.curTick(),
        'exit_cause': event.getCause(), 'exit_code': event.getCode(),
        'history_protection': args.history_protection,
        'finite_source_transport': 'NOT_INSTANTIATED',
        'conditional_query_admission_latency_cycles': args.query_latency,
        **({'conditional_query_hash_latch_cycles': 1, 'conditional_query_row_return_cycles': 1,
            'history_query_trace_phase': 'hash capture'}
           if args.query_pipeline else {}),
        **({'conditional_training_admissions_per_cycle': 1} if args.single_training_port else {}),
        'cpu_cycle_ticks': args.cycle_ticks, 'lease_period_raw_appends': args.lease_period,
        'lease_service_cycles': args.lease_service_cycles,
        'lease_service_scope': 'own raw; quiescent restore-owner drain; no physical stage-fit assertion',
        'post_exit_advance_ticks': 0,
        'native_branch_history_may_remain_at_architectural_exit': True,
        'performance_scope': 'program completion, no observer/drain time added',
    }, indent=2)+'\n')
    print('Exit cause:', event.getCause(), 'code:', event.getCode(), 'tick:', m5.curTick())
    if not (success or detected_stop):
        raise RuntimeError('unexpected program termination')
    return root


if __name__ == '__m5_main__':
    root = main()
