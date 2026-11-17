"""Export committed conditional query operands as B0 port activity."""
import argparse
import csv
import gzip
from pathlib import Path


PORTS = (('pc_i', 32, '!'), ('path_i', 16, '"'), ('raw_i', 130, '#'), ('fold_i', 200, '$'))
TAG_WIDTHS = (9, 9, 10, 10, 11, 11, 12)


def operands(row):
    raw = sum(int(row[f'raw_limb{i}']) << (64*i) for i in range(3))
    widths = [width for tag in TAG_WIDTHS for width in (9, tag, tag-1)]
    words = list(map(int, row['folds'].split(';')))
    if len(words) != len(widths):
        raise ValueError('unexpected native fold geometry')
    folds, offset = 0, 0
    for value, width in zip(words, widths):
        if not 0 <= value < 1 << width:
            raise ValueError('native fold exceeds declared width')
        folds |= value << offset
        offset += width
    return int(row['pc']) & 0xffffffff, int(row['path']), raw, folds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trace', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--skip', type=int, required=True)
    parser.add_argument('--queries', type=int, required=True)
    parser.add_argument('--interval-ps', type=int, required=True)
    args = parser.parse_args()
    if args.skip < 0 or args.queries < 2 or args.interval_ps < 1:
        parser.error('nonnegative skip, at least two queries and positive interval required')
    with gzip.open(args.trace, 'rt', newline='') as src, args.output.open('x') as out:
        out.write('$timescale 1ps $end\n$scope module query_ports $end\n')
        for name, width, code in PORTS:
            out.write(f'$var wire {width} {code} {name} [{width-1}:0] $end\n')
        out.write('$upscope $end\n$enddefinitions $end\n')
        count = 0
        for row in csv.DictReader(src):
            if row['conditional'] != '1':
                continue
            if args.skip:
                args.skip -= 1
                continue
            out.write(f'#{count * args.interval_ps}\n')
            for value, (_, width, code) in zip(operands(row), PORTS):
                if not 0 <= value < 1 << width:
                    raise ValueError('native operand exceeds port width')
                out.write(f'b{value:0{width}b} {code}\n')
            count += 1
            if count == args.queries:
                break
        if count != args.queries:
            raise ValueError('trace ended before requested query count')
        out.write(f'#{count * args.interval_ps}\n')
    print(f'{count} committed query operands at {args.interval_ps} ps intervals')


if __name__ == '__main__':
    main()
