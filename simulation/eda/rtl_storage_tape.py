"""Generate paired K1 tapes on the physical history-pipeline RTL catalog."""
import argparse
import json
from pathlib import Path
import re

from radiation.fixed import REFERENCE_CYCLE_TICKS
from radiation.rng import descriptor
from simulation.analysis.catalog_tapes import coupled_events, digest
from .rtl_storage_catalog import EXTRA, bindings


def generate(output, seed, horizon, intensity):
    catalogs = {variant: {(path, bit): category for path, bit, category in bindings(variant)}
                for variant in EXTRA}
    events = list(coupled_events(seed, horizon, intensity, catalogs))
    output.mkdir(parents=True)
    union = output / 'union.tape'
    with union.open('x') as stream:
        for tick, (path, bit) in events:
            stream.write(f'{tick} {path} {bit}\n')
    arms = {}
    for name, sites in catalogs.items():
        tape = output / f'{name}.tape'
        count = 0
        with tape.open('x') as stream:
            for tick, (path, bit) in events:
                if (path, bit) in sites:
                    stream.write(f'{tick} {path} {bit}\n')
                    count += 1
        arms[name] = dict(bits=len(sites), events=count, tape_sha256=digest(tape))
    report = dict(seed=seed, horizon_ps=horizon, flips_per_bit_second=intensity,
                  coordinate='absolute ps since end of fixed warmup',
                  reference_grid_ps=REFERENCE_CYCLE_TICKS,
                  law='independent K1 events on RTL storage variables',
                  rng={role: descriptor(seed, role) for role in ('time', 'location')},
                  union_events=len(events), union_sha256=digest(union), arms=arms)
    (output / 'tapes.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


def audit(tape, simulation_log):
    planned = [line.split() for line in tape.read_text().splitlines()]
    trace = simulation_log.read_text()
    deliveries = [line.split()[1:] for line in trace.splitlines() if line.startswith('STORAGE_XOR ')]
    summary = re.findall(r'(?m)^PASS_HISTORY_STORAGE_TAPE edges=(\d+) applied=(\d+) responses=(\d+) stopped=(\d+)$',
                         trace)
    if len(summary) != 1 or len(planned) != len(deliveries):
        raise ValueError('missing completion marker or mismatched delivery count')
    for expected, actual in zip(planned, deliveries):
        tick, path, bit = expected
        if actual[:4] != [tick, tick, path, bit] or len(actual) != 6 or set(actual[4:]) != {'0', '1'}:
            raise ValueError(f'incorrect bit or time in delivery at {tick} ps')
    edges, count, responses, stopped = map(int, summary[0])
    if count != len(planned) or not 0 <= max(responses, stopped) <= edges:
        raise ValueError('inconsistent replay summary')
    return dict(tape_sha256=digest(tape), log_sha256=digest(simulation_log),
                edges=edges, applied_events=count, accepted_responses=responses, stopped_edges=stopped)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    create = commands.add_parser('generate')
    create.add_argument('output', type=Path)
    create.add_argument('--seed', type=int, required=True)
    create.add_argument('--horizon-ps', type=int, required=True)
    create.add_argument('--intensity', type=float, required=True)
    check = commands.add_parser('audit')
    check.add_argument('tape', type=Path)
    check.add_argument('simulation_log', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'generate':
            result = generate(args.output, args.seed, args.horizon_ps, args.intensity)
        else:
            result = audit(args.tape, args.simulation_log)
        print(json.dumps(result, indent=2))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
