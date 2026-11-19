"""Read verified direction and completion observations from a native gem5 run."""
import argparse
import hashlib
import json
from pathlib import Path

PROVIDERS = ('longestMatch', 'altMatch', 'bimodalAltMatch', 'bimodal')
BPU = 'system.cpu.branchPred.'


def stop_stats(path, tick):
    current = None
    matched = None
    for line in path.read_text().splitlines():
        if line.startswith('---------- Begin Simulation Statistics'):
            current = {}
        elif line.startswith('---------- End Simulation Statistics'):
            if current and current.get('finalTick') == str(tick):
                matched = current
            current = None
        elif current is not None:
            fields = line.split()
            if len(fields) >= 2:
                current[fields[0]] = fields[1]
    if matched is None:
        raise ValueError('no complete stats dump at the terminal tick')
    return matched


def completion(run, golden_sha256):
    native = json.loads((run/'native.json').read_text())
    term = json.loads((run/'termination.json').read_text())
    tick = term['program_exit_tick']
    if tick != native['tick'] or term['post_exit_advance_ticks'] or not native['faults_frozen']:
        raise ValueError('terminal tick, frozen counters, or no-drain contract does not hold')
    stats = stop_stats(run/'stats.txt', tick)
    freq = int(stats['simFreq'])
    clock = int(stats['system.clk_domain.clock'])
    instructions = int(stats['simInsts'])
    if (int(stats['simTicks']) != tick or clock != term['cpu_cycle_ticks']
            or instructions != native['retired_instructions'] or min(freq, clock) <= 0):
        raise ValueError('timing or retired-instruction provenance mismatch')

    def provider_total(outcome):
        prefix = BPU+'conditionalBranchPred.tage.'
        return sum(int(stats[prefix+provider+'Provider'+outcome]) for provider in PROVIDERS)

    correct, wrong = provider_total('Correct'), provider_total('Wrong')
    conditionals = sum(int(stats[BPU+'committed_0::'+name]) for name in ('DirectCond', 'IndirectCond'))
    if correct+wrong != conditionals or conditionals != native['conditional_updates']:
        raise ValueError('direction outcomes do not match committed conditional updates')

    stdout = run/'program.stdout'
    observed = hashlib.sha256(stdout.read_bytes()).hexdigest() if stdout.is_file() else None
    status = term['status']
    if status == 'PASS' and term['exit_code'] == 0:
        if observed is None:
            raise ValueError('normal termination lacks program stdout')
        status = 'correct' if observed == golden_sha256 else 'sdc'
    elif (status == 'DETECTED_STOP' and term.get('history_protection') == 'ecc_halt'
          and native.get('history_protection_halted') and native.get('protection_due_words')):
        status = 'detected_stop'
    elif status == 'FAIL' and term['exit_cause'] == 'simulate() limit reached':
        status = 'timeout'
    else:
        raise ValueError('unexpected or unclassified simulator outcome')
    if native['schedule_exhausted_before_exit']:
        raise ValueError('fault tape did not cover the terminal tick')
    return {
        'status': status, 'output_sha256': observed, 'golden_sha256': golden_sha256,
        'roi_start_tick': 0, 'roi_end_tick': tick, 'ticks_per_second': freq,
        'clock_period_ticks': clock, 'retired_instructions': instructions,
        'conditional_predictions': conditionals, 'direction_correct': correct, 'direction_wrong': wrong,
        'direction_accuracy_pct': 100*correct/conditionals if conditionals else None,
        'direction_mpki': 1000*wrong/instructions if instructions else None,
        'completion_ms': 1000*tick/freq if status == 'correct' else None,
        'completion_cycles': tick/clock if status == 'correct' else None,
        'events_applied': native['applied_events'], 'flipped_bits_applied': native['applied_flips'],
        'tape_horizon_tick': native['declared_tape_horizon_tick'],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--golden-stdout', type=Path, required=True)
    args = parser.parse_args()
    try:
        digest = hashlib.sha256(args.golden_stdout.read_bytes()).hexdigest()
        print(json.dumps(completion(args.run, digest), indent=2))
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
