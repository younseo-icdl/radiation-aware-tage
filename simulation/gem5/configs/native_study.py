"""Unprotected native TAGE, explicit bit flips, and read-only recovery traces.

No common finite controller or assumed protection latency is added. This
configuration supplies UF and actual branch-time observations; it is not a
pristine certification campaign or a physical timing qualification.
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
    if args.max_ticks <= 0:
        parser.error('max-ticks must be positive')
    output = Path(m5.options.outdir).resolve()
    base = NativeTAGEBase(minHist=5, maxHist=130, takenOnlyHistory=False,
        speculativeHistUpdate=True,
        schedule_file=str(args.schedule.resolve()) if args.schedule else '',
        event_file=str(output/'events.csv'), summary_file=str(output/'native.json'),
        manifest_file=str(output/'logical_manifest.json'),
        origin_file=str(output/'raw_origins.csv') if args.diagnostics else '')
    predictor = NativeTAGE(tage=base,
        commit_trace_file=str(output/'committed.csv.gz') if args.diagnostics else '')
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
    (output/'termination.json').write_text(json.dumps({
        'status': 'PASS' if success else 'FAIL', 'program_exit_tick': m5.curTick(),
        'exit_cause': event.getCause(), 'exit_code': event.getCode(),
        'additional_transport': 'NOT_INSTANTIATED', 'post_exit_advance_ticks': 0,
        'native_branch_history_may_remain_at_architectural_exit': True,
        'performance_scope': 'program completion, no observer/drain time added',
    }, indent=2)+'\n')
    print('Exit cause:', event.getCause(), 'code:', event.getCode(), 'tick:', m5.curTick())
    if not success:
        raise RuntimeError('unexpected program termination')
    return root


if __name__ == '__m5_main__':
    root = main()
