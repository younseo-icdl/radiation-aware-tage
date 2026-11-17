"""Fixed SOURCE/WHOLE comparison laws, separate from legacy/conditional tapes."""
import argparse
import json
import math
from pathlib import Path
from .rng import rng, descriptor

NOMINAL_HZ = 2000000000
TICKS_PER_SECOND = 1000000000000
REFERENCE_CYCLE_TICKS = 500
SOURCE_EVENTS_PER_SECOND = 2000
CROSS_SECTION_CM2 = 1.05e-14
FLUX_PER_CM2_HOUR = 20
WHOLE_SCALES = (10**15, 10**16)


def per_bit_rate(scale):
    if scale not in WHOLE_SCALES:
        raise ValueError('WHOLE scale must be the fixed 1e15 or 1e16 condition')
    return CROSS_SECTION_CM2*FLUX_PER_CM2_HOUR/3600*scale


def arrival_ticks(seed, horizon_ticks, events_per_second, max_events=1000000):
    """Continuous Poisson time, rounded up on the fixed nominal reference grid.

    Candidate CPU clock changes do not change this grid or events/second. A
    Quantized events beyond the requested horizon are future events. Regenerating
    a longer tape from the same seed preserves the complete shorter prefix.
    """
    if (isinstance(horizon_ticks, bool) or not isinstance(horizon_ticks, int)
            or horizon_ticks <= 0 or max_events <= 0):
        raise ValueError('positive integer horizon/event bound required')
    if not math.isfinite(events_per_second) or events_per_second <= 0:
        raise ValueError('positive finite event rate required')
    clock = rng(seed, 'time')
    time, count = 0.0, 0
    while True:
        time += float(clock.exponential(NOMINAL_HZ/events_per_second))
        if time > horizon_ticks/REFERENCE_CYCLE_TICKS:
            return
        position=max(1, math.ceil(time))*REFERENCE_CYCLE_TICKS
        if position>horizon_ticks:
            return
        if count >= max_events:
            raise ValueError('event bound exceeded; no rate truncation is allowed')
        yield position
        count += 1


def source_events(seed, horizon_ticks, max_events=1000000):
    marks, locations = rng(seed, 'K'), rng(seed, 'location')
    for tick in arrival_ticks(seed, horizon_ticks, SOURCE_EVENTS_PER_SECOND, max_events):
        k = 1 if int(marks.integers(214)) < 205 else 2
        start = int(locations.integers(130-k+1))
        yield tick, tuple('R{}'.format(start+i) for i in range(k))


def whole_events(seed, horizon_ticks, semantic_union, scale, max_events=1000000):
    """One union tape; absent design sites are thinned without redrawing time.

    Callers freeze the augmented semantic union and map each emitted key to
    their own actual stored bit or absent site. This function does not certify
    that a supplied population covers every predictor/checkpoint/control bit.
    """
    keys = list(semantic_union)
    if not keys or any(not isinstance(k, str) or not k for k in keys) or len(set(keys))!=len(keys):
        raise ValueError('a nonempty unique semantic bit union is required')
    keys.sort()
    locations = rng(seed, 'location')
    rate = len(keys)*per_bit_rate(scale)
    for tick in arrival_ticks(seed, horizon_ticks, rate, max_events):
        yield tick, keys[int(locations.integers(len(keys)))]


def schedule(environment, seed, horizon_ticks, catalog=None, max_events=1000000):
    if environment == 'SOURCE':
        if catalog is not None:
            raise ValueError('SOURCE raw130 does not accept a WHOLE catalog')
        rows = list(source_events(seed, horizon_ticks, max_events))
        rate = SOURCE_EVENTS_PER_SECOND
        union_size = applicable_size = 130
        no_site = 0
    else:
        if environment not in ('WHOLE_1e15', 'WHOLE_1e16') or not isinstance(catalog, dict):
            raise ValueError('WHOLE requires a semantic-key to token/null catalog')
        if any(token is not None and (not isinstance(token, str) or not token or
                                     any(c.isspace() for c in token) or ';' in token)
               for token in catalog.values()):
            raise ValueError('one stored-bit token or null is required per semantic key')
        tokens = [t for t in catalog.values() if t is not None]
        if len(tokens) != len(set(tokens)):
            raise ValueError('distinct semantic bits cannot alias a stored-bit token')
        scale = WHOLE_SCALES[environment == 'WHOLE_1e16']
        union = list(whole_events(seed, horizon_ticks, catalog, scale, max_events))
        rows = [(tick, (catalog[key],)) for tick, key in union if catalog[key] is not None]
        no_site = len(union)-len(rows)
        union_size, applicable_size = len(catalog), len(tokens)
        rate = union_size*per_bit_rate(scale)
    info = {'environment': environment, 'seed': seed, 'time_unit': 'ticks',
            'ticks_per_second': TICKS_PER_SECOND, 'reference_cycle_ticks': REFERENCE_CYCLE_TICKS,
            'nominal_reference_hz': NOMINAL_HZ, 'requested_horizon_ticks': horizon_ticks,
            'coverage_end_tick': horizon_ticks,
            'last_reference_grid_tick': (horizon_ticks//REFERENCE_CYCLE_TICKS)*REFERENCE_CYCLE_TICKS,
            'events_per_second_union': rate, 'union_bits': union_size,
            'applicable_bits': applicable_size, 'emitted_union_events': len(rows)+no_site,
            'applicable_events': len(rows), 'absent_site_events': no_site,
            'coverage_scope': 'DECLARED_CATALOG_ONLY_NOT_WHOLE_CERTIFICATE',
            'physical_rate_calibration': 'ASSUMED_FIXED_COMPARISON_NOT_NEW_MEASUREMENT',
            'historical_tape_identity': 'NOT_ASSERTED; current namespace-v2 implementation is explicit',
            'source_multiplicity': 'integer K<205 of 214 => K1, else K2; no expected-K rate division'
                                   if environment == 'SOURCE' else 'K1',
            'equal_tick_records': 'distinct events, not merged into MCU',
            'rng': {r: descriptor(seed, r) for r in ('time', 'K', 'location')}}
    return rows, info


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--environment', choices=['SOURCE', 'WHOLE_1e15', 'WHOLE_1e16'], required=True)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--horizon-ticks', type=int, required=True)
    p.add_argument('--catalog', type=Path, help='JSON semantic bit -> native token/null; same frozen union for all designs')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--max-events', type=int, default=1000000)
    a = p.parse_args()
    sidecar = a.output.with_name(a.output.name+'.json')
    if a.output.exists() or sidecar.exists():
        p.error('schedule/descriptor exists; use a fresh output path')
    try:
        catalog = json.loads(a.catalog.read_text()) if a.catalog else None
        rows, info = schedule(a.environment, a.seed, a.horizon_ticks, catalog, a.max_events)
    except (ValueError, OSError) as error:
        p.error(str(error))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open('x') as f:
        f.write('# time_unit=ticks environment={} seed={} horizon={} rng_namespace=2\n'.format(
            a.environment, a.seed, a.horizon_ticks))
        for tick, sites in rows:
            f.write('{} {}\n'.format(tick, ';'.join(sites)))
    with sidecar.open('x') as f:
        f.write(json.dumps(info, indent=2)+'\n')
    print(json.dumps(info))


if __name__ == '__main__':
    main()
