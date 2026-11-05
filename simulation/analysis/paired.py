"""Paired-owner A/B/C/D cycle analysis; failures remain visible in the output."""
import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
import numpy as np


def summarize(rows, seed=548, bootstrap=10000):
    if bootstrap < 100:
        raise ValueError('use at least 100 bootstrap resamples')
    groups = defaultdict(dict)
    for row in rows:
        key = row['program'], row['candidate']
        owner, cell = row['owner'], row['cell']
        if cell not in 'ABCD' or len(cell) != 1:
            raise ValueError('cell must be A, B, C, or D')
        cells = groups[key].setdefault(owner, {})
        if cell in cells:
            raise ValueError('duplicate owner/cell: ' + str((key, owner, cell)))
        status = row['status']
        value = float(row['cycles']) if status == 'PASS' else None
        if value is not None and (not math.isfinite(value) or value <= 0):
            raise ValueError('PASS cycles must be finite and positive')
        cells[cell] = (status, value)
    output = []
    for (program, candidate), owners in sorted(groups.items()):
        failures = Counter(status for cells in owners.values() for status, _ in cells.values() if status != 'PASS')
        complete = [cells for _, cells in sorted(owners.items())
                    if set(cells) == set('ABCD') and all(c[0] == 'PASS' for c in cells.values())]
        record = {'program': program, 'candidate': candidate, 'owners': len(owners),
                  'complete_pass_pairs': len(complete), 'excluded_owners': len(owners) - len(complete),
                  'failed_cells_by_status': dict(failures),
                  'incomplete_owners': sum(set(cells) != set('ABCD') for cells in owners.values())}
        if complete:
            values = np.array([[cells[cell][1] for cell in 'ABCD'] for cells in complete])
            a, b, c, d = values.T
            net = b - d
            rng = np.random.Generator(np.random.PCG64(seed))
            # Resample matched owners as units, never individual A/B/C/D cells.
            means = np.empty(bootstrap)
            for index in range(bootstrap):
                means[index] = net[rng.integers(0, len(net), len(net))].mean()
            record.update({'mean_cycles': dict(zip('ABCD', map(float, values.mean(axis=0)))),
                           'net_B_minus_D_cycles': float(net.mean()),
                           'net_B_minus_D_95pct_paired_bootstrap_CI': list(map(float, np.quantile(means, [.025, .975]))) if len(net) > 1 else None,
                           'clean_C_minus_A_cycles': float((c - a).mean()),
                           'fault_penalty_B_minus_A_cycles': float((b - a).mean()),
                           'residual_D_minus_C_cycles': float((d - c).mean()),
                           'mean_owner_net_percent_of_A': float(np.mean(100 * net / a)),
                           'CI_note': 'conditional on complete PASS owners; failures are reported separately'})
        output.append(record)
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('input', type=Path, help='CSV: program,candidate,owner,cell,cycles,status')
    p.add_argument('--seed', type=int, default=548)
    p.add_argument('--bootstrap', type=int, default=10000)
    a = p.parse_args()
    with a.input.open(newline='') as source:
        result = summarize(list(csv.DictReader(source)), a.seed, a.bootstrap)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
