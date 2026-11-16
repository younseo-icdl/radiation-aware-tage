"""Recompute wide A/B/C/D tables without merging timing contracts or owners.

Accepts method/policy, scenario/condition, and valid_pair/pair_valid aliases.
MPKI columns describe D; --clean supplies C and the unprotected row supplies B.
Missing MPKI remains null. Shared clean controls are not independent samples.
"""
import argparse
from collections import Counter, defaultdict
import csv
import json
import math
from pathlib import Path
from statistics import mean


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def method(row):
    return row.get('method', row.get('policy', row.get('candidate')))


def condition(row):
    return row.get('scenario', row.get('condition', 'unspecified'))


def boolean(value):
    if value in (True, 'True', 'true', '1'):
        return True
    if value in (False, 'False', 'false', '0'):
        return False
    raise ValueError('expected explicit Boolean, got ' + repr(value))


def valid(row):
    flags = [boolean(row[key]) for key in ('valid_pair', 'pair_valid', 'program_correct')
             if key in row]
    if not flags and 'status' not in row:
        raise ValueError('each pair requires validity or status')
    return (all(flags) and row.get('status', 'PASS') == 'PASS'
            and row.get('reference_status', 'PASS') == 'PASS'
            and not row.get('failure'))


def cycles(value):
    result = int(value)
    if result <= 0:
        raise ValueError('cycles must be positive integers')
    return result


def mpki(row, name):
    value = row.get(name)
    if value is None or value == '':
        return None
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError('MPKI must be finite and nonnegative')
    return value


def decomposition(a, b, c, d):
    return {'fault_B_minus_A': b-a, 'clean_C_minus_A': c-a,
            'residual_D_minus_C': d-c, 'net_B_minus_D': b-d}


def describe(values):
    values = [value for value in values if value is not None]
    return {'n': len(values), 'mean': mean(values) if values else None,
            'min': min(values) if values else None,
            'max': max(values) if values else None}


def analyze(rows, clean_rows, *, unprotected, contract, cohort):
    if not contract.strip() or not cohort.strip() or not unprotected:
        raise ValueError('explicit contract, cohort, and unprotected method are required')
    clean = {}
    for row in clean_rows:
        key = row['program'], method(row)
        if key in clean:
            raise ValueError('duplicate clean program/method ' + str(key))
        clean[key] = row
    indexed = {}
    for row in rows:
        for key, expected in (('contract', contract), ('cohort', cohort)):
            if row.get(key, expected) != expected:
                raise ValueError('mixed ' + key + ' values; analyze each separately')
        if not method(row) or not row['owner']:
            raise ValueError('method and independent owner are required')
        key = row['program'], condition(row), row['owner'], method(row)
        if key in indexed:
            raise ValueError('duplicate program/condition/owner/method ' + str(key))
        indexed[key] = row
    samples, groups = [], defaultdict(list)
    for (program, scenario, owner, candidate), row in sorted(indexed.items()):
        passed = valid(row)
        sample = {'program': program, 'condition': scenario, 'owner': owner,
                  'candidate': candidate, 'valid_pair': passed, 'raw': row,
                  'metrics': {}, 'mpki': {}}
        if passed:
            a, b, c, d = (cycles(row[cell]) for cell in 'ABCD')
            sample['metrics'].update({cell+'_cycles': value
                                      for cell, value in zip('ABCD', (a, b, c, d))})
            delta = decomposition(a, b, c, d)
            sample['metrics'].update({key+'_cycles': value for key, value in delta.items()})
            sample['metrics'].update({key+'_percent_A': 100*value/a for key, value in delta.items()})
            sample['metrics']['net_percent_B'] = 100*(b-d)/b
            base = indexed.get((program, scenario, owner, unprotected))
            if base is None or not valid(base):
                raise ValueError('valid pair lacks valid unprotected owner ' + str((program, scenario, owner)))
            if (cycles(base['A']), cycles(base['B']), cycles(base['C']), cycles(base['D'])) != (a, b, a, b):
                raise ValueError('A/B disagree with the unprotected owner')
            own_clean, base_clean = clean.get((program, candidate)), clean.get((program, unprotected))
            for control, expected in ((own_clean, c), (base_clean, a)):
                if clean_rows and control is None:
                    raise ValueError('missing clean control ' + str((program, candidate)))
                if control is not None and (cycles(control['cycles']) != expected
                                             or control.get('status', 'PASS') != 'PASS'):
                    raise ValueError('clean control disagrees with A/C')
            for name in ('conditional_MPKI', 'all_branch_MPKI'):
                values = [mpki(control or {}, name) for control in (base_clean, base, own_clean, row)]
                sample['mpki'][name] = dict(zip('ABCD', values))
                # A missing measure is never inferred from cycles, IPC, or a stall counter.
                pairs = {'fault_B_minus_A': (1, 0), 'clean_C_minus_A': (2, 0),
                         'residual_D_minus_C': (3, 2), 'net_B_minus_D': (1, 3)}
                differences = {key: values[left]-values[right]
                               if values[left] is not None and values[right] is not None else None
                               for key, (left, right) in pairs.items()}
                sample['mpki'][name].update(differences)
        samples.append(sample)
        groups[program, scenario, candidate].append(sample)
    summaries = []
    for (program, scenario, candidate), members in sorted(groups.items()):
        complete = [row for row in members if row['valid_pair']]
        metric_names = sorted(set().union(*(row['metrics'] for row in complete)))
        summary = {'program': program, 'condition': scenario, 'candidate': candidate,
                   'owners': len(members), 'valid_owners': len(complete),
                   'invalid_owners': len(members)-len(complete),
                   'failures': dict(Counter(row['raw'].get('failure')
                                          or (row['raw'].get('status') if row['raw'].get('status') != 'PASS' else None)
                                          or 'INVALID_PAIR' for row in members if not row['valid_pair'])),
                   'metrics': {name: describe(row['metrics'][name] for row in complete)
                               for name in metric_names}, 'mpki': {}}
        for name in ('conditional_MPKI', 'all_branch_MPKI'):
            summary['mpki'][name] = {key: describe(row['mpki'][name][key] for row in complete)
                                    for key in ('A', 'B', 'C', 'D', *decomposition(0, 0, 0, 0))}
        for name in ('fault_B_minus_A_cycles', 'residual_D_minus_C_cycles', 'net_B_minus_D_cycles'):
            values = [row['metrics'][name] for row in complete]
            summary[name+'_signs'] = {'positive': sum(v > 0 for v in values),
                                     'zero': sum(v == 0 for v in values),
                                     'negative': sum(v < 0 for v in values)}
        summaries.append(summary)
    return {'contract': contract, 'cohort': cohort, 'unprotected': unprotected,
            'scope': 'Reported paired CPU cycles; no new CPU trials or hardware cost measurements.',
            'statistics': 'Owner mean and observed range, conditional on valid pairs; not confidence bounds.',
            'missing_mpki': 'Null means unavailable; absence is not zero.',
            'pair_rows': len(samples), 'samples': samples, 'summaries': summaries}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--clean', type=Path)
    parser.add_argument('--unprotected', required=True)
    parser.add_argument('--contract', required=True, help='Timing/producer comparison contract; never rename finite P0 native')
    parser.add_argument('--cohort', required=True, help='Keep development, evaluation, and different inputs separate')
    args = parser.parse_args()
    result = analyze(read_csv(args.input), read_csv(args.clean) if args.clean else [],
                     unprotected=args.unprotected, contract=args.contract, cohort=args.cohort)
    result['input'] = str(args.input.resolve())
    result['clean_input'] = str(args.clean.resolve()) if args.clean else None
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
