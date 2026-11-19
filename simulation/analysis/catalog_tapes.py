"""Create paired native tapes with a fixed intensity per cataloged storage bit."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

from radiation.fixed import arrival_ticks
from radiation.rng import descriptor, rng


def storage_sites(manifest):
    """Map a semantic storage token to the fault ID in one native manifest."""
    result = {}

    def add(token, site):
        if token in result or not isinstance(site, int) or site < 0:
            raise ValueError(f'duplicate token or invalid ID for {token}')
        result[token] = site

    for word in manifest['words']:
        if not word['consumed']:
            continue
        index, ids = word['word'], word['site_ids']
        if len(ids) != word['width']:
            raise ValueError(f'manifest word {index} has inconsistent width')
        for bit, site in enumerate(ids):
            add(f'W{index}:{bit}', site)
    for entry in manifest['protection_sites']:
        word, bit, replica = (entry[key] for key in ('word', 'bit', 'replica'))
        structure = entry['structure']
        if structure == 'secded_check':
            add(f'C{word}:{bit}', entry['id'])
        elif structure == 'replica':
            add(f'T{replica}:{word}:{bit}', entry['id'])
        else:
            raise ValueError(f'unknown protection storage {structure}')
    for bit in range(manifest['lease_age_bits']):
        add(f'L:AGE:{bit}', manifest['lease_age_sites_start']+bit)
    if not result or len(set(result.values())) != len(result):
        raise ValueError('catalog is empty or two semantic tokens alias the same storage')
    return result


def coupled_events(seed, horizon, intensity, catalogs, max_events=1000000):
    if not catalogs or any(not sites for sites in catalogs.values()):
        raise ValueError('every design must expose a nonempty storage catalog')
    if not math.isfinite(intensity) or intensity <= 0:
        raise ValueError('intensity must be positive and finite')
    union = sorted({site for sites in catalogs.values() for site in sites})
    selection = rng(seed, 'location')
    for tick in arrival_ticks(seed, horizon, intensity*len(union), max_events):
        yield tick, union[int(selection.integers(len(union)))]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def generate(manifests, output, seed, horizon, intensity, max_events=1000000):
    if any(not name.isidentifier() for name in manifests):
        raise ValueError('arm names must be identifiers')
    catalogs = {name:storage_sites(json.loads(path.read_text())) for name,path in manifests.items()}
    events = list(coupled_events(seed, horizon, intensity, catalogs, max_events))
    output.mkdir(parents=True)
    shared = output/'semantic-union.events'
    with shared.open('x') as stream:
        stream.write(f'# time_unit=ticks horizon={horizon} environment=CATALOG_K1\n')
        for tick, mark in events:
            stream.write(f'{tick} {mark}\n')
    info = dict(seed=seed, horizon_ticks=horizon, flips_per_bit_second=intensity,
                law='K1 fixed per cataloged bit', union_events=len(events),
                union_tape_sha256=digest(shared),
                rng={role:descriptor(seed, role) for role in ('time','location')}, arms={})
    for name, sites in catalogs.items():
        schedule = output/(name+'.events')
        rows = [(tick, mark) for tick,mark in events if mark in sites]
        with schedule.open('x') as stream:
            stream.write(f'# time_unit=ticks horizon={horizon} environment=CATALOG_K1\n')
            for tick, mark in rows:
                stream.write(f'{tick} {mark}\n')
        info['arms'][name] = dict(bits=len(sites), events_per_second=intensity*len(sites),
                                 retained_events=len(rows), excluded_union_events=len(events)-len(rows),
                                 manifest_sha256=digest(manifests[name]), tape_sha256=digest(schedule))
    with (output/'tapes.json').open('x') as stream:
        json.dump(info, stream, indent=2)
        stream.write('\n')
    return info


def audit_delivery(run, tape):
    """Verify terminal delivery by storage ID for a generated single-bit tape."""
    state = json.loads((run/'native.json').read_text())
    sites = storage_sites(json.loads((run/'logical_manifest.json').read_text()))
    with tape.open() as stream:
        header = dict(field.split('=',1) for field in next(stream).split()[1:])
        if (header.get('time_unit'), header.get('environment')) != ('ticks','CATALOG_K1'):
            raise ValueError('expected catalog K1 in absolute ticks')
        horizon = int(header['horizon'])
        planned = [(int(tick),sites[mark]) for tick,mark in map(str.split,stream)]
    stop = state['tick']
    expected = [(tick,site) for tick,site in planned if tick <= stop]
    with (run/'events.csv').open() as stream:
        actual = list(csv.DictReader(stream))
    if len(actual) != len(expected):
        raise ValueError('injected events do not match the eligible tape prefix')
    for i, ((tick,site), row) in enumerate(zip(expected,actual),1):
        fields = ('event_ordinal','requested_tick','applied_tick','multiplicity','logical_site_ids')
        if (tuple(int(row[key]) for key in fields) != (i,tick,tick,1,site) or
                {row['bit_values_before'],row['bit_values_after']} != {'0','1'}):
            raise ValueError(f'injection does not match catalog at event {i}')
    summary = dict(declared_tape_horizon_tick=horizon, scheduled_events=len(planned),
                   applied_events=len(expected), applied_flips=len(expected),
                   future_events_censored=len(planned)-len(expected),
                   schedule_exhausted_before_exit=stop>horizon)
    if not state['faults_frozen'] or any(state[key]!=value for key,value in summary.items()):
        raise ValueError('native terminal counters disagree with the catalog tape')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='action', required=True)
    create = subs.add_parser('generate')
    create.add_argument('--arm',action='append',nargs=2,metavar=('NAME','MANIFEST'),required=True)
    create.add_argument('--seed',type=int,required=True)
    create.add_argument('--horizon-ticks',type=int,required=True)
    create.add_argument('--intensity',type=float,required=True,help='single-bit flips per bit per second')
    create.add_argument('--output',type=Path,required=True)
    check = subs.add_parser('audit')
    check.add_argument('run',type=Path)
    check.add_argument('tape',type=Path)
    args = parser.parse_args()
    try:
        if args.action=='generate':
            manifests={arm:Path(path) for arm,path in args.arm}
            if len(manifests)!=len(args.arm):
                raise ValueError('duplicate arm name')
            summary=generate(manifests,args.output,args.seed,args.horizon_ticks,args.intensity)
        else:
            summary=audit_delivery(args.run,args.tape)
        print(json.dumps(summary,indent=2))
    except (OSError, KeyError, ValueError) as error:
        parser.error(str(error))


if __name__=='__main__':
    main()
