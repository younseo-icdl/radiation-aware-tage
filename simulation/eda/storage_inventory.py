"""Audit mapped history-subsystem registers against the RTL and native exposure scopes."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re

from simulation.analysis.catalog_tapes import storage_sites

MODULE = re.compile(r'(?ms)^[ \t]*module\s+(\w+)\b[^;]*;(.*?)^[ \t]*endmodule\b')
INSTANCE = re.compile(r'(?m)^[ \t]+([\w$]+)\s+(\\\S+\s+|[\w$]+\s*)\(')
CELL = re.compile(r'(?m)^\s*cell\s*\(\s*"?(\w+)"?\s*\)\s*\{')
REGISTERS = {
    'raw_mem': 'raw_ring', 'head': 'history_head', 'folds': 'active_folds',
    'path': 'active_path', 'path_checkpoint': 'checkpoints',
    'pending': 'query_packet', 'pending_owner': 'query_packet',
    'pending_path_bit': 'query_packet', 'row_request_token_o': 'query_packet',
    'row_request_pc_o': 'query_packet', 'row_request_index_o': 'query_packet',
    'row_request_tag_o': 'query_packet',
}
BASE = dict(raw_ring=1024, history_head=10, active_folds=200,
            active_path=16, checkpoints=512*16, query_packet=194)
# SECDED check storage is 9 raw bits, 6 path bits, and 106 folded
# history bits. The 12-bit tag fold requires five Hamming parity bits
# and one overall bit. The other 20 fold words each require five total.
SECDED_CHECK_BITS = 9 + 6 + 20*5 + 6
EXTRA = {
    'unprotected': {},
    'lease': dict(lease_age=13, lease_timer=2),
    'ecc': dict(secded_check=SECDED_CHECK_BITS, secded_failed=1),
    'ecc_refill': dict(secded_check=SECDED_CHECK_BITS, secded_failed=1, refill_control=11),
    'tmr': dict(tmr_replica=2*346),
}


def liberty_cells(path):
    source = path.read_text()
    matches = list(CELL.finditer(source))
    if not matches:
        raise ValueError('Liberty library has no supported cell declarations')
    result = {}
    for index, match in enumerate(matches):
        end = matches[index+1].start() if index+1 < len(matches) else len(source)
        state = re.findall(r'(?m)^\s*(ff|latch|ff_bank|latch_bank)\s*\(', source[match.end():end])
        result[match[1]] = tuple(state)
    return result


def classify(instance):
    field = re.sub(r'_reg(?:\[\d+\])*(?:_\w+)?$', '', instance)
    leaf = field.rsplit('.', 1)[-1]
    if leaf in REGISTERS:
        return REGISTERS[leaf]
    if leaf in ('replica_a', 'replica_b'):
        return 'tmr_replica'
    if leaf == 'check':
        return 'secded_check'
    if leaf == 'failed':
        return 'secded_failed'
    if field.endswith('lease.controller.age') or leaf == 'age':
        return 'lease_age'
    if leaf in ('remaining', 'phase', 'base_only_o'):
        return 'refill_control' if 'refill' in field.split('.')[:-1] else 'lease_timer'
    return 'unclassified'


def mapped_storage(path, top, library):
    modules = {name: body for name, body in MODULE.findall(path.read_text())}
    if top not in modules:
        raise ValueError(f'mapped top {top} missing')
    registers = []
    totals = Counter()

    def walk(module, scope, stack):
        if module in stack:
            raise ValueError('recursive mapped module hierarchy')
        for master, raw_name in INSTANCE.findall(modules[module]):
            name = raw_name.strip().lstrip('\\')
            instance = f'{scope}.{name}' if scope else name
            if master in modules:
                walk(master, instance, (*stack, module))
            else:
                if master not in library:
                    raise ValueError(f'{instance}: unknown mapped master {master}')
                totals[master] += 1
                state = library[master]
                if state:
                    if state != ('ff',):
                        raise ValueError(f'{instance}: unsupported sequential master {master}')
                    registers.append(dict(instance=instance, master=master, category=classify(instance)))

    walk(top, '', ())
    if not registers or len({row['instance'] for row in registers}) != len(registers):
        raise ValueError('missing or duplicate mapped register instances')
    return registers, totals


def inventory(variant, synthesis, liberty, manifest=None):
    top = (synthesis / 'TOP.txt').read_text().strip()
    registers, cells = mapped_storage(synthesis / 'mapped.v', top, liberty_cells(liberty))
    # Reconcile the netlist traversal with the top-level producer report so an
    # unrecognized instance syntax cannot silently reduce the mapped count.
    area = (synthesis / 'reports/area.rpt').read_text()
    row = re.search(rf'(?m)^\s*{re.escape(top)}\s+NA\s+(\d+)\s+([0-9.]+)', area)
    if row is None or int(row[1]) != cells.total():
        raise ValueError('mapped instance count disagrees with the Genus area report')
    declared = {**BASE, **EXTRA[variant]}
    mapped = Counter(item['category'] for item in registers)
    if 'unclassified' in mapped:
        names = [row['instance'] for row in registers if row['category'] == 'unclassified']
        raise ValueError(f'unclassified mapped register examples: {", ".join(names[:8])}')
    native = None
    if manifest:
        tokens = storage_sites(json.loads(manifest.read_text()))
        native = dict(active_history=sum(token.startswith('W') for token in tokens),
                      check_bits=sum(token.startswith('C') for token in tokens),
                      replica_bits=sum(token.startswith('T') for token in tokens),
                      control_bits=sum(token.startswith('L:AGE:') for token in tokens),
                      covered_bits=len(tokens))
    report = dict(variant=variant, top=top, logical_active_payload_bits=346,
                  rtl_declared_counts=declared, rtl_declared_total=sum(declared.values()),
                  synthesized_ff_counts=dict(mapped), synthesized_ff_total=len(registers),
                  mapped_minus_declared={category: mapped[category] - declared.get(category, 0)
                                         for category in sorted(mapped.keys() | declared.keys())
                                         if mapped[category] != declared.get(category, 0)},
                  synthesized_stdcell_total=cells.total(), synthesized_cell_area_um2=float(row[2]),
                  native_injectable_catalog=native,
                  provenance_sha256={label: hashlib.sha256(path.read_bytes()).hexdigest()
                                     for label, path in (
                                         ('mapped_verilog', synthesis / 'mapped.v'), ('liberty', liberty),
                                         ('area_report', synthesis / 'reports/area.rpt'),
                                         ('logical_manifest', manifest)) if path is not None})
    return report, registers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('variant', choices=EXTRA)
    parser.add_argument('synthesis', type=Path)
    parser.add_argument('--liberty', type=Path, required=True)
    parser.add_argument('--native-manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        report, registers = inventory(args.variant, args.synthesis, args.liberty, args.native_manifest)
        args.output.mkdir(parents=True)
        (args.output / 'inventory.json').write_text(json.dumps(report, indent=2) + '\n')
        with (args.output / 'mapped-registers.csv').open('x', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=registers[0])
            writer.writeheader()
            writer.writerows(registers)
    except (KeyError, OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
