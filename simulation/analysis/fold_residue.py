"""Summarize bounded native own-raw fold inconsistency episodes."""
import argparse
from collections import Counter
import csv
from itertools import groupby
import json
from pathlib import Path

DIMENSIONS = ('any_bank', *(f'bank{i}' for i in range(1, 8)))
OPERATIONS = {'append', 'restore', 'publish', 'before_injection', 'after_injection'}


def duration_summary(rows, begin, stop, injections):
    if not 0 <= begin <= stop:
        raise ValueError('invalid stop-bounded observation window')
    rows = list(rows)
    previous = (begin, 0)
    seen = Counter()
    for row in rows:
        tick, appends = int(row['tick']), int(row['raw_appends'])
        op = row['operation']
        bits = [int(row[bank]) for bank in DIMENSIONS[1:]]
        if (not begin <= tick <= stop or tick < previous[0] or appends < previous[1]
                or min(*bits, int(row['active_raw_origin_labels'])) < 0 or op not in OPERATIONS):
            raise ValueError('invalid fold residue observation')
        if op == 'publish' and any(bits):
            raise ValueError('own-raw refold did not restore consistency at publication')
        if op.endswith('_injection'):
            seen[tick, op] += 1
        previous = tick, appends
    for op in ('before_injection', 'after_injection'):
        if Counter({tick: count for (tick, item), count in seen.items() if item == op}) != injections:
            raise ValueError('fold residue observation is missing an applied injection boundary')

    states = []
    for tick, group in groupby(rows, key=lambda row: int(row['tick'])):
        last = list(group)[-1]
        banks = [bool(int(last[bank])) for bank in DIMENSIONS[1:]]
        states.append((tick, [any(banks), *banks], int(last['active_raw_origin_labels']) > 0))
    first = states[0][0] if states else stop
    first_banks = [bool(int(rows[0][bank])) for bank in DIMENSIONS[1:]] if rows else [False] * 7
    first_present = [any(first_banks), *first_banks]
    episodes = {name: [] for name in DIMENSIONS}
    starts = [None] * len(DIMENSIONS)
    no_origins = [0] * len(DIMENSIONS)
    for i, (tick, present, origin) in enumerate(states):
        end = states[i+1][0] if i+1 < len(states) else stop
        for j, active in enumerate(present):
            if active and end > tick:
                if starts[j] is None:
                    starts[j] = tick
                if not origin:
                    no_origins[j] += end - tick
            elif not active and starts[j] is not None:
                episodes[DIMENSIONS[j]].append(dict(start_tick=starts[j], end_tick=tick,
                    left_censored=starts[j] == first and first_present[j], right_censored=False))
                starts[j] = None
    for name, start, present in zip(DIMENSIONS, starts, first_present):
        if start is not None:
            episodes[name].append(dict(start_tick=start, end_tick=stop,
                left_censored=start == first and present, right_censored=True))
    return dict(start_tick=begin, first_observed_tick=first if states else None, stop_tick=stop,
                observed_ticks=stop-first, applied_injections=sum(injections.values()),
                dimensions={name: dict(mismatch_ticks=sum(e['end_tick']-e['start_tick'] for e in episodes[name]),
                                       mismatch_ticks_without_active_raw_origin_labels=absent,
                                       episodes=episodes[name]) for name, absent in zip(DIMENSIONS, no_origins)})


def summarize(run):
    term = json.loads((run / 'termination.json').read_text())
    begin, limit = (term[key] for key in ('fold_residue_start_tick', 'fold_residue_end_tick'))
    terminal = term['program_exit_tick']
    stop = max(begin, min(limit, terminal))
    with (run / 'events.csv').open(newline='') as stream:
        ticks = (int(row['applied_tick']) for row in csv.DictReader(stream))
        injections = Counter(tick for tick in ticks if begin <= tick < limit and tick <= terminal)
    with (run / 'fold_residue.csv').open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    if any(int(row['tick']) >= limit or int(row['tick']) > terminal for row in rows):
        raise ValueError('observer record exceeds its exclusive limit or architectural exit')
    return duration_summary(rows, begin, stop, injections)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(summarize(args.run), indent=2))
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
