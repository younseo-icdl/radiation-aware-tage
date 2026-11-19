"""Compare matched native completion and classify fetch opportunities blocked by lease service."""
import argparse
from configparser import ConfigParser
import csv
import hashlib
import json
from pathlib import Path

from .native_completion import completion


def read_json(path):
    return json.loads(path.read_text())


def lease_counters(run, clock, elapsed, service_cycles, enabled):
    native = read_json(run / 'native.json')
    config = ConfigParser(interpolation=None)
    with (run / 'config.ini').open() as stream:
        config.read_file(stream)
    if any(config.getint('system.cpu', key) != 1 for key in ('numThreads', 'smtNumFetchingThreads')):
        raise ValueError('fetch wait counters require one thread and one fetch attempt per CPU cycle')
    drain = native['lease_drain_wait_calls']
    service = native['lease_service_wait_calls']
    blocked = native['lease_frontend_wait_calls']
    publications = native['lease_publications']
    censored = native['lease_completion_censored_at_exit']
    if (min(drain, service, blocked, publications) < 0 or drain + service != blocked
            or blocked > (elapsed + clock - 1) // clock or censored != native['lease_busy_at_exit']):
        raise ValueError('lease waits are not an exclusive, stop-bounded fetch partition')

    if not enabled:
        if blocked or publications or censored:
            raise ValueError('lease activity occurred with the lease disabled')
        return dict(drain_fetch_cycles=0, service_fetch_cycles=0, blocked_fetch_cycles=0,
                    published_leases=0, censored_lease=False, service_window_ticks=0)

    published = 0
    pending = None
    last_tick = -1
    with (run / 'lease_events.csv').open(newline='') as stream:
        for row in csv.DictReader(stream):
            tick, ready = int(row['tick']), int(row['ready_tick'])
            if not last_tick < tick <= elapsed or tick % clock or int(row['live_owners']) != 0:
                raise ValueError('lease ledger has invalid timing or live owners')
            if row['event'] == 'start' and pending is None and ready == tick + service_cycles * clock:
                pending = ready
            elif row['event'] == 'publish' and tick == ready == pending and int(row['age']) == 0:
                published += 1
                pending = None
            else:
                raise ValueError('lease start/publication sequence disagrees with the service contract')
            last_tick = tick
    if published != publications or (pending is not None) != censored or (censored and pending < elapsed):
        raise ValueError('lease ledger and stop snapshot disagree')
    service_ticks = published * service_cycles * clock
    if censored:
        service_ticks += elapsed - last_tick
    if service > published * service_cycles + (service_cycles if censored else 0):
        raise ValueError('service fetch blocks exceed the available service windows')
    return dict(drain_fetch_cycles=drain, service_fetch_cycles=service, blocked_fetch_cycles=blocked,
                published_leases=published, censored_lease=censored, service_window_ticks=service_ticks)


def compare(run_root, base_record, lease_record):
    base, lease = [read_json(path)['run'] for path in (base_record, lease_record)]
    keys = ('pair_id', 'workload', 'seed_id', 'fault_law_id', 'reference_rate_eps',
            'shared_tape_sha256', 'exposure_policy', 'timing_contract', 'clock_period_ticks',
            'ticks_per_second', 'git_commit', 'input_sha256', 'golden_sha256')
    if ((base['method'], lease['method']) != ('unprotected', 'rebuild')
            or any(base[key] != lease[key] for key in keys)
            or base['timing_contract'] != 'matched'):
        raise ValueError('records are not a matched unprotected/lease pair')
    verified = []
    for row, enabled in ((base, False), (lease, True)):
        run = run_root / row['run_id']
        if hashlib.sha256((run / 'config.ini').read_bytes()).hexdigest() != row['config_sha256']:
            raise ValueError('run config differs from its recorded SHA-256')
        observed = completion(run, row['golden_sha256'])
        timing = read_json(run / 'termination.json')
        clock, elapsed = observed['clock_period_ticks'], observed['roi_end_tick']
        if (any(row[key] != observed[key] for key in (
                'status', 'clock_period_ticks', 'ticks_per_second', 'roi_start_tick', 'roi_end_tick',
                'retired_instructions', 'direction_correct', 'direction_wrong', 'events_applied'))
                or timing['lease_period_raw_appends'] != int(row['rebuild_interval_appends'])
                or (timing['lease_period_raw_appends'] > 0) != enabled
                or timing['lease_service_cycles'] <= 0):
            raise ValueError('run record disagrees with terminal measurements')
        verified.append((observed, lease_counters(run, clock, elapsed, timing['lease_service_cycles'], enabled)))
    control, candidate = [value[0] for value in verified]
    joint = control['status'] == candidate['status'] == 'correct'
    return dict(
        **{key: base[key] for key in keys[:5]},
        unprotected={**control, **verified[0][1]}, lease={**candidate, **verified[1][1]},
        lease_minus_unprotected_cycles=(candidate['completion_cycles'] - control['completion_cycles']) if joint else None,
        lease_minus_unprotected_direction_mpki=(candidate['direction_mpki'] - control['direction_mpki']) if joint else None,
        lease_minus_unprotected_direction_misses=(candidate['direction_wrong'] - control['direction_wrong']) if joint else None,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_root', type=Path)
    parser.add_argument('unprotected_record', type=Path)
    parser.add_argument('lease_record', type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(compare(args.run_root, args.unprotected_record, args.lease_record), indent=2))
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
