"""Emit physical-bit bindings for the fixed history pipeline RTL boundary."""
import argparse
from collections import Counter
from pathlib import Path

from .storage_inventory import BASE, EXTRA

TAG_WIDTHS = (9, 9, 10, 10, 11, 11, 12)


def bindings(variant):
    """Return (RTL variable, bit index, category), with stable physical ring coordinates."""
    fields = [
        ('history.raw_mem', 1024, 'raw_ring'), ('history.head', 10, 'history_head'),
        ('history.folds', 200, 'active_folds'), ('history.path', 16, 'active_path'),
        *((f'history.path_checkpoint[{row}]', 16, 'checkpoints') for row in range(512)),
        *((name, width, 'query_packet') for name, width in (
            ('pending', 1), ('pending_owner', 9), ('pending_path_bit', 1),
            ('row_request_token_o', 16), ('row_request_pc_o', 32),
            ('row_request_index_o', 63), ('row_request_tag_o', 72))),
    ]
    if variant == 'lease':
        fields += [('history.lease.controller.age', 13, 'lease_age'),
                   ('history.lease.controller.remaining', 2, 'lease_timer')]
    if variant in ('ecc', 'ecc_refill'):
        fields += [('history.ecc_raw.check', 9, 'secded_check'),
                   ('history.ecc_path.check', 6, 'secded_check'),
                   ('history.ecc_raw.failed', 1, 'secded_failed')]
    if variant == 'ecc_refill':
        fields += [('refill.phase', 2, 'refill_control'), ('refill.remaining', 8, 'refill_control'),
                   ('refill.base_only_o', 1, 'refill_control')]
    for bank, tag_width in enumerate(TAG_WIDTHS):
        for kind, width in enumerate((9, tag_width, tag_width-1)):
            word = f'history.bank[{bank}].word[{kind}]'
            if variant in ('ecc', 'ecc_refill'):
                fields.append((f'{word}.ecc.check', 6 if width == 12 else 5, 'secded_check'))
            if variant == 'tmr':
                fields += [(f'{word}.tmr.replica_{replica}', width, 'tmr_replica') for replica in 'ab']
    if variant == 'tmr':
        fields += [(f'history.tmr_{word}.replica_{replica}', width, 'tmr_replica')
                   for word, width in (('raw', 130), ('path', 16)) for replica in 'ab']

    result = [(name, bit, category) for name, width, category in fields for bit in range(width)]
    if len({(name, bit) for name, bit, _ in result}) != len(result):
        raise ValueError('storage catalog has aliased physical keys')
    if Counter(category for _, _, category in result) != {**BASE, **EXTRA[variant]}:
        raise ValueError('physical bindings and RTL inventory disagree')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant', choices=EXTRA)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    try:
        with args.output.open('x') as stream:
            for name, bit, category in bindings(args.variant):
                stream.write(f'{name} {bit} {category}\n')
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
