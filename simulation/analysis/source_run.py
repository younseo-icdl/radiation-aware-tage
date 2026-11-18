"""Audit the fixed SOURCE tape against an elapsed native CPU run."""
import argparse
import csv
import json
from pathlib import Path

from radiation.fixed import REFERENCE_CYCLE_TICKS, source_events


def load_tape(path):
    with path.open() as stream:
        header = next(stream, '').split()
        if header[:1] != ['#']:
            raise ValueError('SOURCE tape header missing')
        meta = dict(field.split('=', 1) for field in header[1:])
        if (meta.get('time_unit'), meta.get('environment'), meta.get('rng_namespace')) != (
            'ticks', 'SOURCE', '2',
        ):
            raise ValueError('expected fixed SOURCE in absolute ticks with RNG namespace 2')
        horizon = int(meta['horizon'])
        if horizon <= 0 or horizon % REFERENCE_CYCLE_TICKS:
            raise ValueError('SOURCE tape horizon is off the fixed reference grid')
        events = []
        for row in stream:
            tick, marks = row.split()
            events.append((int(tick), tuple(marks.split(';'))))
    if events != list(source_events(int(meta['seed']), horizon)):
        raise ValueError('tape differs from the declared fixed SOURCE seed and horizon')
    return events, horizon


def integers(cell):
    return tuple(map(int, cell.split(';')))


def check_delivery(run, tape=None):
    state = json.loads((run/'native.json').read_text())
    exit_tick = state['tick']
    expected, horizon = load_tape(tape) if tape else ([], 0)
    manifest = json.loads((run/'logical_manifest.json').read_text())
    raw, = [entry['site_ids'] for entry in manifest['words']
            if entry['name'] == 'raw_path:0' and entry['width'] == 130]
    if len(raw) != 130 or len(set(raw)) != 130:
        raise ValueError('raw manifest must have 130 unique sites')
    due = [(tick, marks) for tick, marks in expected if tick <= exit_tick]
    with (run/'events.csv').open(newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != [
            'event_ordinal', 'requested_tick', 'applied_tick', 'multiplicity',
            'logical_site_ids', 'raw_physical_indices', 'bit_values_before', 'bit_values_after',
        ]:
            raise ValueError('native SOURCE event trace has an invalid header')
        applied = list(reader)
    if len(applied) != len(due):
        raise ValueError('observed injections differ from the expected time prefix')
    flips = 0
    for ordinal, (row, (tick, marks)) in enumerate(zip(applied, due), 1):
        sites = tuple(raw[int(mark[1:])] for mark in marks)
        if (int(row['event_ordinal']), int(row['requested_tick']), int(row['applied_tick']),
                int(row['multiplicity']), integers(row['logical_site_ids'])) != (
            ordinal, tick, tick, len(sites), sites,
        ):
            raise ValueError(f'SOURCE coordinate or order mismatch at event {ordinal}')
        physical = integers(row['raw_physical_indices'])
        before, after = (integers(row[key]) for key in ('bit_values_before', 'bit_values_after'))
        if (len(physical) != len(sites) or physical[0] < 0 or
                physical != tuple(range(physical[0], physical[0]+len(sites))) or
                len(before) != len(after) or len(before) != len(sites) or
                any((a, b) not in ((0, 1), (1, 0)) for a, b in zip(before, after))):
            raise ValueError(f'SOURCE event {ordinal} did not XOR its contiguous raw sites')
        flips += len(sites)
    summary = dict(scheduled_events=len(expected), applied_events=len(due),
                   applied_flips=flips, future_events_censored=len(expected)-len(due),
                   declared_tape_horizon_tick=horizon,
                   schedule_exhausted_before_exit=bool(horizon and exit_tick > horizon))
    if not state['faults_frozen'] or any(state[key] != value for key, value in summary.items()):
        raise ValueError('native exit summary disagrees with the independently checked tape')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--tape', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(check_delivery(args.run, args.tape), indent=2))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
