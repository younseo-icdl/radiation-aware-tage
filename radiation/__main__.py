"""Generate an external schedule consumed by C++ replay or gem5."""
import argparse
from pathlib import Path
from .models import events


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed', type=int, required=True)
    p.add_argument('--horizon', type=int, required=True)
    p.add_argument('--rate', type=float, help='events per declared exposure unit')
    p.add_argument('--single', action='store_true')
    p.add_argument('--scope', choices=['raw', 'sstar'], default='raw')
    p.add_argument('--multiplicity', choices=['single', 'charm', 'cern'], default='charm')
    p.add_argument('--catalog', type=Path, help='whole CERN cluster text file, required for cern')
    p.add_argument('--mapping', choices=['contiguous', 'interleaved', 'dispersed'], default='contiguous')
    p.add_argument('--time-unit', choices=['branches', 'cycles'], required=True)
    p.add_argument('--ticks-per-cycle', type=int, default=500)
    p.add_argument('--max-events', type=int, default=1000000)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.ticks_per_cycle <= 0:
        p.error('ticks-per-cycle must be positive')
    if a.output.exists():
        p.error('output already exists; choose a new experiment path')
    try:
        if a.multiplicity == 'cern':
            if not a.catalog or a.scope != 'sstar':
                p.error('cern requires --catalog and --scope sstar')
            from .cern import parse
            from .empirical import cern_marks
            marks = cern_marks(parse(a.catalog.read_text()), a.seed, a.mapping)
            positions = events(a.seed, a.horizon, a.rate, 'sstar', a.single, 'single', a.max_events)
            rows = [(position, next(marks)) for position, _ in positions]
        else:
            if a.catalog:
                p.error('--catalog requires --multiplicity cern')
            rows = list(events(a.seed, a.horizon, a.rate, a.scope, a.single,
                               a.multiplicity, a.max_events))
    except ValueError as error:
        p.error(str(error))
    a.output.parent.mkdir(parents=True, exist_ok=True)
    scale = a.ticks_per_cycle if a.time_unit == 'cycles' else 1
    with a.output.open('x') as out:
        out.write('# time_unit={} seed={} horizon={} rate={} scope={} multiplicity={} catalog={} mapping={} rng_namespace=2\n'.format(
            a.time_unit, a.seed, a.horizon, a.rate, a.scope, a.multiplicity, a.catalog, a.mapping))
        for position, sites in rows:
            out.write('{} {}\n'.format(position * scale, ';'.join(sites)))
    print('{} events -> {}'.format(len(rows), a.output))


if __name__ == '__main__':
    main()
