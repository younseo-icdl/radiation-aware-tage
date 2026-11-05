"""Reusable validation and acquisition of the public radiation datasets."""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import urllib.request
from .cern import parse

FLYING_COLUMNS = ['Lon (deg)', 'Lat (deg)', 'Alt (m)',
                  'Timestamp (ms UTC Unix)', 'Time', 'Position Source']


def flying_audit(path):
    """Count complete records and timestamps; duplicates are not MCUs."""
    with Path(path).open(newline='', encoding='utf-8-sig') as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != FLYING_COLUMNS:
            raise ValueError('unexpected Flying Laptop columns')
        rows = list(reader)
    records, timestamps = Counter(), Counter()
    for line, row in enumerate(rows, 2):
        if None in row or any(row[k] is None or row[k] == '' for k in FLYING_COLUMNS):
            raise ValueError('incomplete CSV row {}'.format(line))
        lon, lat, alt = (float(row[k]) for k in FLYING_COLUMNS[:3])
        if not all(math.isfinite(v) for v in (lon, lat, alt)) or not (-180 <= lon <= 180 and -90 <= lat <= 90):
            raise ValueError('invalid coordinates at row {}'.format(line))
        records[tuple(row[k] for k in FLYING_COLUMNS)] += 1
        timestamps[int(row[FLYING_COLUMNS[3]])] += 1
    if not rows:
        raise ValueError('empty CSV')
    return {'raw_rows': len(rows), 'distinct_complete_records': len(records),
            'duplicate_extra_rows': len(rows) - len(records),
            'distinct_timestamps': len(timestamps),
            'timestamp_group_sizes': dict(Counter(timestamps.values())),
            'interpretation': 'record audit only; no MCU classification or calibrated per-bit rate'}


def fetch_cern(destination, names=None, require_clean=True):
    """Cache provider-verified bytes and audit each complete cluster file.

    A parser rejection never deletes verified source bytes. Cache-only callers
    can retain anomalous records for review; strict model qualification stays
    the default and uses the unchanged cluster parser.
    """
    catalog = json.loads(Path(__file__).with_name('datasets.json').read_text())
    listed = {entry['name']: entry for entry in catalog['files']}
    names = names or catalog['default_subset']
    if any(name not in listed for name in names):
        raise ValueError('filename outside the published dataset catalog')
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    for name in names:
        entry = listed[name]
        target = destination / name
        if target.exists():
            raw = target.read_bytes()
        else:
            request = urllib.request.Request(entry['url'], headers={'User-Agent': 'radiation-aware-tage/1.0'})
            with urllib.request.urlopen(request, timeout=30) as response:
                raw = response.read(100 * 1024 * 1024 + 1)
        if len(raw) > 100 * 1024 * 1024 or hashlib.md5(raw).hexdigest() != entry['md5']:
            raise ValueError('provider MD5 mismatch or size limit: ' + name)
        if not target.exists():
            with target.open('xb') as output:
                output.write(raw)
        result = {'file': str(target), 'bytes': len(raw), 'provider_md5_verified': True}
        try:
            clusters = parse(raw.decode('utf-8'))  # Audit the ENTIRE file.
        except ValueError as error:
            if require_clean:
                raise ValueError('strict parser rejected {}: {}'.format(name, error)) from error
            result.update(parse_status='REVIEW_REQUIRED', parse_error=str(error), clusters=None)
        else:
            result.update(parse_status='PASS', clusters=len(clusters))
        yield result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest='command', required=True)
    cern = commands.add_parser('cern', help='parse and validate a whole cluster file')
    cern.add_argument('input', type=Path)
    flying = commands.add_parser('flying', help='audit complete CSV records and duplicate timestamps')
    flying.add_argument('input', type=Path)
    flying.add_argument('--schedule', type=Path, help='optional explicit compressed detection replay')
    flying.add_argument('--horizon', type=int)
    flying.add_argument('--time-unit', choices=['branches', 'cycles'])
    flying.add_argument('--seed', type=int, default=548)
    flying.add_argument('--duplicates', choices=['collapse', 'preserve'], default='collapse')
    flying.add_argument('--timing', choices=['observed', 'permuted', 'fixed-count-poisson'], default='observed')
    flying.add_argument('--multiplicity', choices=['single', 'charm'], default='single')
    fetch = commands.add_parser('fetch-cern', help='download and fully validate public cluster files')
    fetch.add_argument('--destination', type=Path, required=True)
    selection = fetch.add_mutually_exclusive_group()
    selection.add_argument('--names', nargs='+')
    selection.add_argument('--all', action='store_true', help='fetch every file in the provider catalog')
    fetch.add_argument('--cache-only', action='store_true',
                       help='retain MD5-verified files and report parser anomalies for review')
    a = p.parse_args()
    if a.command == 'cern':
        rows = parse(a.input.read_text())
        result = {'clusters': len(rows),
                  'coordinate_multiplicity': dict(Counter(r['multiplicity_from_unique_coordinates'] for r in rows)),
                  'suspected_origin_ids': [r['cluster_id'] for r in rows if r['suspected_origin_sentinel']]}
    elif a.command == 'flying':
        result = flying_audit(a.input)
        if a.schedule:
            if a.horizon is None or a.time_unit is None:
                p.error('--schedule requires --horizon and --time-unit')
            from .empirical import flying_events
            with a.input.open(newline='', encoding='utf-8-sig') as source:
                timestamps = [int(row[FLYING_COLUMNS[3]]) for row in csv.DictReader(source)]
            records = flying_events(timestamps, a.seed, a.horizon, a.duplicates, a.timing, a.multiplicity)
            scale = 500 if a.time_unit == 'cycles' else 1
            a.schedule.parent.mkdir(parents=True, exist_ok=True)
            with a.schedule.open('x') as output:
                output.write('# time_unit={} detection_replay={} duplicates={} seed={} multiplicity={} target_rate_calibrated=false\n'.format(
                    a.time_unit, a.timing, a.duplicates, a.seed, a.multiplicity))
                for row in records:
                    output.write('{} {}\n'.format(row['position']*scale, ';'.join(row['sites'])))
            result['schedule'] = str(a.schedule)
            result['replay_records'] = len(records)
    else:
        names = a.names
        if a.all:
            catalog = json.loads(Path(__file__).with_name('datasets.json').read_text())
            names = [entry['name'] for entry in catalog['files']]
        result = list(fetch_cern(a.destination, names, require_clean=not a.cache_only))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
