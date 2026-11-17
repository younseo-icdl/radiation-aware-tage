"""Paired completion-time benefit with explicit owner resampling and failures."""
import argparse
import csv
import json
import math
from pathlib import Path
import numpy as np


def paired_summary(rows, *, seed, replicates=10000, confidence=0.95):
    if replicates < 1 or not 0 < confidence < 1:
        raise ValueError('invalid uncertainty parameters')
    owners, benefits, failed = set(), [], []
    for row in rows:
        owner = row['owner_id']
        if owner in owners:
            raise ValueError('duplicate owner: resampling unit must be unique')
        owners.add(owner)
        valid = row.get('pair_valid') in (True, 'true', 'True', '1')
        if not valid or row['UF_status'] != 'PASS' or row['MF_status'] != 'PASS':
            failed.append(owner)
            continue
        uf, mf = float(row['UF_cycles']), float(row['MF_cycles'])
        if not all(math.isfinite(v) and v > 0 for v in (uf, mf)):
            raise ValueError('a valid pair needs finite positive completion cycles')
        benefits.append(100*(uf-mf)/uf)
    result = {'total_owners': len(owners), 'valid_pairs': len(benefits),
              'failed_or_noncomparable_owners': failed,
              'estimand': 'mean owner percent benefit 100*(UF-MF)/UF',
              'resampling_unit': 'paired event owner, not individual runs or instructions',
              'interval_scope': 'exploratory small-owner percentile bootstrap; no workload or physical-environment generalization',
              'runtime_scope': 'CONDITIONAL_ON_VALID_PAIRS' if failed else 'ALL_DECLARED_PAIRS',
              'seed': seed, 'replicates': replicates, 'confidence': confidence,
              'mean_benefit_percent': None, 'ci_lower_percent': None, 'ci_upper_percent': None,
              'decision': 'INSUFFICIENT_VALID_OWNERS'}
    if not benefits:
        return result
    values = np.asarray(benefits)
    result.update(mean_benefit_percent=float(values.mean()),
                  sample_std_percent=float(values.std(ddof=1)) if len(values)>1 else None,
                  minimum_benefit_percent=float(values.min()), maximum_benefit_percent=float(values.max()),
                  positive_owners=int((values>0).sum()), zero_owners=int((values==0).sum()),
                  negative_owners=int((values<0).sum()))
    if len(values) < 2:
        return result
    rng = np.random.default_rng(seed)
    draws = values[rng.integers(0, len(values), size=(replicates, len(values)))].mean(axis=1)
    low, high = np.quantile(draws, [(1-confidence)/2, (1+confidence)/2], method='linear')
    result.update(ci_lower_percent=float(low), ci_upper_percent=float(high))
    if failed:
        result['decision'] = 'NO_ALL_OWNER_CLAIM_FAILURES_OR_NONCOMPARABLE_PAIRS'
    elif low > 0:
        result['decision'] = 'POSITIVE_IN_DECLARED_OWNER_MODEL'
    elif high < 0:
        result['decision'] = 'NEGATIVE_IN_DECLARED_OWNER_MODEL'
    else:
        result['decision'] = 'SUPERIORITY_NOT_ESTABLISHED'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pairs', type=Path, help='CSV: owner_id, UF/MF_status, UF/MF_cycles, pair_valid')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--replicates', type=int, default=10000)
    a = p.parse_args()
    if a.output.exists():
        p.error('output exists; choose a fresh file')
    with a.pairs.open() as f:
        result = paired_summary(csv.DictReader(f), seed=a.seed, replicates=a.replicates)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        f.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
