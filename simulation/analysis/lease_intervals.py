"""Analyze paired lease-period ablations against disabled and own-clean controls."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
from statistics import mean

from .sweep_design import VALID_OUTCOMES, outcomes

PERIODS = (0, 1024, 2048, 4096, 8192, 16384)
MATCH = ('clock_period_ticks', 'ticks_per_second', 'input_sha256', 'golden_sha256',
         'timing_contract', 'exposure_policy', 'git_commit', 'shared_tape_sha256')


def summarize(rows):
    groups = defaultdict(dict)
    scope = {}
    for row in rows:
        workload, law, seed = (row[key] for key in ('workload', 'fault_law_id', 'seed_id'))
        rate, period = (int(row[key]) for key in ('reference_rate_eps', 'rebuild_interval_appends'))
        key = workload, rate, law, seed
        if (period not in PERIODS or period in groups[key] or row['status'] not in VALID_OUTCOMES
                or rate < 0 or (rate == 0) != (law == 'clean_reference')
                or (rate == 0) != (seed == 'clean')):
            raise ValueError('unexpected, duplicate or unresolved interval observation')
        contract = tuple(row[key] for key in MATCH[:-1])
        if scope.setdefault(workload, contract) != contract:
            raise ValueError('interval clean and faulted runs changed timing or input provenance')
        groups[key][period] = row
    clean = {}
    cells = defaultdict(list)
    for (workload, rate, law, _seed), arms in groups.items():
        if set(arms) != set(PERIODS) or any(
                len({row[key] for row in arms.values()}) != 1 for key in MATCH):
            raise ValueError('interval comparison requires six arms at the same timing, input and tape')
        measured = {period: outcomes(row) for period, row in arms.items()}
        if rate == 0:
            if any(value is None for value in measured.values()):
                raise ValueError('all six clean interval controls must complete correctly')
            clean[workload] = measured
        else:
            cells[workload, rate, law].append(measured)
    if not cells or {workload for workload, _, _ in cells} != set(clean):
        raise ValueError('missing faulted pairs or clean controls')

    results = []
    for (workload, rate, law), pairs in sorted(cells.items()):
        controls = clean[workload]
        clock, frequency = map(int, scope[workload][:2])
        cycles_per_second = frequency / clock
        for period in PERIODS:
            observed = [pair[period] for pair in pairs if pair[period] is not None]
            joint = [(pair[0], pair[period]) for pair in pairs
                     if pair[0] is not None and pair[period] is not None]
            seconds, mpki = controls[period]
            results.append(dict(
                workload=workload, reference_rate_eps=rate, fault_law_id=law, interval_appends=period,
                total_pairs=len(pairs), correct=len(observed),
                joint_correct_vs_disabled=len(joint), clean_ms=1000*seconds, clean_mpki=mpki,
                clean_cycles=seconds*cycles_per_second,
                clean_minus_disabled_ms=1000*(seconds-controls[0][0]),
                clean_minus_disabled_mpki=mpki-controls[0][1],
                paired_mean_delta_ms=mean(1000*(b[0]-a[0]) for a, b in joint) if joint else None,
                paired_mean_delta_cycles=mean((b[0]-a[0])*cycles_per_second
                                              for a, b in joint) if joint else None,
                paired_mean_delta_mpki=mean(b[1]-a[1] for a, b in joint) if joint else None,
                mean_own_clean_delta_ms=mean(1000*(elapsed-seconds) for elapsed, _ in observed)
                                        if observed else None,
                mean_own_clean_delta_mpki=mean(value-mpki for _, value in observed) if observed else None))
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', type=Path)
    args = parser.parse_args()
    try:
        with args.runs.open(newline='') as stream:
            print(json.dumps(summarize(csv.DictReader(stream)), indent=2))
    except (OSError, ValueError, KeyError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
