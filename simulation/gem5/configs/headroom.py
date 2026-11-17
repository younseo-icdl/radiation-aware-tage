"""Small base-output diagnostic and actual minimal bimodal architecture controls."""
import argparse
import json
from pathlib import Path
import sys
import m5
from m5.objects import Root, NativeTAGE, NativeTAGEBase, BimodalMin
sys.path.insert(0, str(Path(__file__).resolve().parent))
from baseline import create_system


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--input', type=Path)
    p.add_argument('--model', choices=['BASE_FORCED', 'BASE_MIN', 'U_NATIVE'], required=True)
    p.add_argument('--fault-tick', type=int, default=0)
    p.add_argument('--fault-site', type=int, default=0,
                   help='Common base prediction bits then shared hysteresis bits')
    p.add_argument('--max-ticks', type=int, default=2000000000000)
    p.add_argument('--seed', type=int, default=548)
    a = p.parse_args()
    if not a.binary.is_file() or (a.input and not a.input.is_file()):
        p.error('missing binary/input')
    if a.fault_tick < 0 or not 0 <= a.fault_site < 10240 or a.max_ticks <= 0:
        p.error('invalid timing or common base site')
    out = Path(m5.options.outdir).resolve()
    if a.model == 'BASE_MIN':
        observer = predictor = BimodalMin(log_size=13, hysteresis_ratio=2,
            summary_file=str(out/'native.json'), fault_tick=a.fault_tick, fault_site=a.fault_site)
    else:
        schedule = ''
        if a.fault_tick:
            file = out/'base.events'
            file.write_text('# time_unit=ticks\n{} {}\n'.format(a.fault_tick, a.fault_site))
            schedule = str(file)
        observer = NativeTAGEBase(minHist=5, maxHist=130, takenOnlyHistory=False,
            speculativeHistUpdate=True, schedule_file=schedule,
            event_file=str(out/'events.csv'), summary_file=str(out/'native.json'),
            manifest_file=str(out/'logical_manifest.json'))
        predictor = NativeTAGE(tage=observer, force_base=a.model == 'BASE_FORCED')
    system = create_system(a, out, predictor)
    root = Root(full_system=False, system=system)
    m5.core.seedRandom(a.seed)
    m5.instantiate()
    event = m5.simulate(a.max_ticks)
    observer.dumpResearch()
    m5.stats.dump()
    success = event.getCause() == 'exiting with last active thread context' and event.getCode() == 0
    (out/'termination.json').write_text(json.dumps({'status': 'PASS' if success else 'FAIL',
        'model': a.model, 'tick': m5.curTick(), 'exit_code': event.getCode(),
        'cause': event.getCause(), 'post_exit_advance_ticks': 0,
        'environment': 'forced single common base-counter bit; not WHOLE',
        'removed_history_fault_sites': 'NOT_APPLICABLE' if a.model == 'BASE_MIN' else None,
        'physical_timing_energy_area': 'UNKNOWN'}, indent=2)+'\n')
    if not success:
        raise RuntimeError('unexpected program termination')
    return root


if __name__ == '__m5_main__':
    root = main()
