"""Audit the fixed SOURCE tape against an elapsed native CPU run."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from radiation.fixed import REFERENCE_CYCLE_TICKS, SOURCE_EVENTS_PER_SECOND, SOURCE_LAWS, source_events
from radiation.rng import descriptor, rng


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
    if events != list(source_events(int(meta['seed']), horizon,
                                    rate=int(meta.get('rate', SOURCE_EVENTS_PER_SECOND)),
                                    law=meta.get('law', SOURCE_LAWS[0]))):
        raise ValueError('tape differs from the declared SOURCE seed, horizon, rate or law')
    return events, horizon


def integers(cell):
    return tuple(map(int, cell.split(';'))) if cell else ()


def map_tmr_tape(shared, destination, seed):
    """Select one mutable replica per event while preserving the shared tape."""
    events, horizon = load_tape(shared)
    replica_stream = rng(seed, 'replica')
    shared_sha256 = hashlib.sha256(shared.read_bytes()).hexdigest()
    with destination.open('x') as out:
        out.write(f'# time_unit=ticks horizon={horizon} shared_sha256={shared_sha256}\n')
        for tick, marks in events:
            replica = int(replica_stream.integers(3))
            mapped = tuple(f'T{replica}:21:{mark[1:]}' for mark in marks) if replica else marks
            out.write(f'{tick} {";".join(mapped)}\n')
    mapped_sha256 = hashlib.sha256(destination.read_bytes()).hexdigest()
    return {'shared_tape_sha256': shared_sha256, 'mapped_tape_sha256': mapped_sha256,
            'events': len(events), 'tape_horizon_tick': horizon, 'replica_rng': descriptor(seed, 'replica')}


def check_delivery(run, tape=None, *, tmr_replica_seed=None):
    state = json.loads((run/'native.json').read_text())
    exit_tick = state['tick']
    expected, horizon = load_tape(tape) if tape else ([], 0)
    manifest = json.loads((run/'logical_manifest.json').read_text())
    raw, = [entry['site_ids'] for entry in manifest['words']
            if entry['name'] == 'raw_path:0' and entry['width'] == 130]
    if len(raw) != 130 or len(set(raw)) != 130:
        raise ValueError('raw manifest must have 130 unique sites')
    replica_stream = None
    copies = [raw]
    if tmr_replica_seed is not None:
        replica_stream = rng(tmr_replica_seed, 'replica')
        for replica in (1, 2):
            sites = {entry['bit']: entry['id'] for entry in manifest['protection_sites']
                     if (entry['structure'], entry['word'], entry['replica']) == ('replica', 21, replica)}
            if set(sites) != set(range(130)):
                raise ValueError('TMR manifest does not contain a complete raw copy')
            copies.append([sites[age] for age in range(130)])
        if len({site for copy in copies for site in copy}) != 390:
            raise ValueError('TMR storage IDs alias across raw copies')
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
        replica = int(replica_stream.integers(3)) if replica_stream is not None else 0
        sites = tuple(copies[replica][int(mark[1:])] for mark in marks)
        if (int(row['event_ordinal']), int(row['requested_tick']), int(row['applied_tick']),
                int(row['multiplicity']), integers(row['logical_site_ids'])) != (
            ordinal, tick, tick, len(sites), sites,
        ):
            raise ValueError(f'SOURCE coordinate or order mismatch at event {ordinal}')
        physical = integers(row['raw_physical_indices'])
        before, after = (integers(row[key]) for key in ('bit_values_before', 'bit_values_after'))
        physical_ok = not physical if replica else (
            len(physical) == len(sites) and physical[0] >= 0 and
            physical == tuple(range(physical[0], physical[0]+len(sites))))
        if (not physical_ok or
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
    parser.add_argument('run', nargs='?', type=Path)
    parser.add_argument('--tape', type=Path)
    parser.add_argument('--map-tmr', type=Path, help='write a native TMR tape from the shared SOURCE tape')
    parser.add_argument('--replica-seed', type=int)
    args = parser.parse_args()
    if args.map_tmr is not None:
        if args.run is not None or args.tape is None or args.replica_seed is None:
            parser.error('TMR mapping requires --tape, --map-tmr, and --replica-seed')
    elif args.run is None or (args.replica_seed is not None and args.tape is None):
        parser.error('provide a run directory for delivery auditing')
    try:
        result = (map_tmr_tape(args.tape, args.map_tmr, args.replica_seed)
                  if args.map_tmr is not None else check_delivery(args.run, args.tape,
                                                                 tmr_replica_seed=args.replica_seed))
        print(json.dumps(result, indent=2))
    except (KeyError, OSError, TypeError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
