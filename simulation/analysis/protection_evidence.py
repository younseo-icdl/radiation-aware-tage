"""Report delivered SOURCE events and native recovery counters for a matched pair."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path

from .native_completion import completion
from .sweep_design import METHODS, VALID_OUTCOMES

PROTECTION = {'ecc': 'ecc_halt', 'ecc_refill': 'ecc_refill', 'tmr': 'tmr'}
RECOVERY_COUNTERS = (
    'protection_word_checks', 'protection_corrected_words', 'protection_due_words',
    'protection_repair_words', 'protection_replica_repairs',
    'refill_resets', 'refill_completed', 'refill_remaining', 'refill_publications',
    'lease_publications', 'lease_drain_wait_calls', 'lease_service_wait_calls',
)
MATCH = (
    'pair_id', 'workload', 'seed_id', 'fault_law_id', 'reference_rate_eps', 'shared_tape_sha256',
    'input_sha256', 'golden_sha256', 'clock_period_ticks', 'ticks_per_second', 'git_commit',
    'exposure_policy', 'timing_contract',
)


def applied_trace(run, method, stop):
    manifest = json.loads((run / 'logical_manifest.json').read_text())
    words = [word for word in manifest['words'] if word['name'] == 'raw_path:0']
    if len(words) != 1 or words[0]['width'] != 130:
        raise ValueError('requires one 130-bit raw history word')
    primary = words[0]
    sites = {site: (0, age) for age, site in enumerate(primary['site_ids'])}
    if method == 'tmr':
        sites.update({row['id']: (row['replica'], row['bit']) for row in manifest['protection_sites']
                      if row['structure'] == 'replica' and row['word'] == primary['word']})
    if len(sites) != (390 if method == 'tmr' else 130):
        raise ValueError(f'{method}: unsupported raw exposure manifest')
    events, counts, copies = [], Counter(), Counter()
    prior = 0
    with (run / 'events.csv').open(newline='') as stream:
        for ordinal, row in enumerate(csv.DictReader(stream), 1):
            multiplicity, wanted, tick, sequence = (int(row[key]) for key in (
                'multiplicity', 'requested_tick', 'applied_tick', 'event_ordinal'))
            targets = [sites[int(site)] for site in row['logical_site_ids'].split(';')]
            replicas, ages = zip(*targets)
            before, after = (row[key].split(';') for key in ('bit_values_before', 'bit_values_after'))
            if (sequence != ordinal or not prior <= tick <= stop or tick <= 0 or wanted != tick
                    or multiplicity not in (1, 2) or len(targets) != multiplicity
                    or len(set(replicas)) != 1 or list(ages) != list(range(ages[0], ages[0]+multiplicity))
                    or len(before) != len(after) or len(before) != multiplicity
                    or any({a, b} != {'0', '1'} for a, b in zip(before, after))):
                raise ValueError(f'{method}: invalid event delivery at ordinal {ordinal}')
            events.append((tick, ages))
            counts[f'K{multiplicity}'] += 1
            copies[f'replica_{replicas[0]}'] += 1
            prior = tick
    return events, counts, copies


def summarize_pair(run_root, rows):
    methods = {row['method']: row for row in rows}
    if (len(rows) != len(METHODS) or set(methods) != set(METHODS)
            or any(len({row[key] for row in rows}) != 1 for key in MATCH)
            or rows[0]['exposure_policy'] != 'common_raw130'):
        raise ValueError('requires a complete matched five-arm raw130 pair')
    measured, trace = {}, {}
    for method in METHODS:
        row = methods[method]
        run = run_root / row['run_id']
        observed = completion(run, row['golden_sha256'])
        native = json.loads((run / 'native.json').read_text())
        status = observed['status']
        if (status not in VALID_OUTCOMES or row['status'] != status
                or native.get('native_history_protection') != PROTECTION.get(method)
                or bool(native.get('history_protection_halted', False)) != (status == 'detected_stop')
                or int(row['roi_end_tick']) != observed['roi_end_tick']
                or int(row['events_applied']) != observed['events_applied']
                or hashlib.sha256((run / 'config.ini').read_bytes()).hexdigest() != row['config_sha256']):
            raise ValueError(f'{method}: inconsistent outcome or native protection mode')
        events, counts, copies = applied_trace(run, method, observed['roi_end_tick'])
        flips = counts['K1'] + 2*counts['K2']
        if (len(events), flips) != (observed['events_applied'], observed['flipped_bits_applied']):
            raise ValueError(f'{method}: event trace differs from frozen terminal counts')
        counters = {key: native[key] for key in RECOVERY_COUNTERS if key in native}
        checks = counters.get('protection_word_checks', 0)
        if (min(counters.values(), default=0) < 0
                or any(counters.get(key, 0)>checks for key in (
                    'protection_due_words','protection_corrected_words','protection_repair_words'))
                or counters.get('refill_completed', 0)>counters.get('refill_resets', 0)):
            raise ValueError(f'{method}: impossible terminal recovery counts')
        measured[method] = dict(status=status, stop_tick=observed['roi_end_tick'],
                                completion_ms=observed['completion_ms'],
                                completion_cycles=observed['completion_cycles'],
                                direction_mpki_at_stop=observed['direction_mpki'],
                                direction_accuracy_pct_at_stop=observed['direction_accuracy_pct'],
                                events=len(events),
                                k1=counts['K1'], k2=counts['K2'], flips=flips,
                                events_by_copy=dict(copies), **counters)
        trace[method] = events
    longest = max(trace.values(), key=len)
    if any(events != longest[:len(events)] for events in trace.values()):
        raise ValueError('arms did not observe prefixes of the same logical tape')
    earliest_stop = min(arm['stop_tick'] for arm in measured.values())
    common = sum(tick <= earliest_stop for tick, _ in longest)
    for arm in measured.values():
        if arm['events'] < common:
            raise ValueError('an event eligible before all stops was skipped')
        arm['events_after_earliest_arm_stop'] = arm['events'] - common
    return dict(**{key: rows[0][key] for key in MATCH}, common_events_through_earliest_stop=common,
                measurements=measured)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_root', type=Path)
    parser.add_argument('records', nargs='*', type=Path)
    parser.add_argument('--runs-csv', type=Path)
    args = parser.parse_args()
    try:
        if args.runs_csv:
            if args.records:
                raise ValueError('provide individual records or a campaign CSV')
            groups = defaultdict(list)
            with args.runs_csv.open(newline='') as stream:
                for row in csv.DictReader(stream):
                    groups[row['pair_id']].append(row)
            if not groups:
                raise ValueError('empty campaign CSV')
            result = [summarize_pair(args.run_root, group) for _, group in sorted(groups.items())]
        else:
            rows = [json.loads(path.read_text())['run'] for path in args.records]
            result = summarize_pair(args.run_root, rows)
        print(json.dumps(result, indent=2))
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
