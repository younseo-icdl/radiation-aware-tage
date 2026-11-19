#!/usr/bin/env python3
"""Directed native O3 check of active-history SECDED halt and TMR repair."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import dataclass
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from checksum import EXPECTED, ROOT


@dataclass(frozen=True)
class Case:
    name: str
    mode: str = 'none'
    schedule: str = ''
    events: int = 0
    repaired_words: int = 0
    halt: bool = False
    lease: bool = False


CASES = (
    Case('ordinary_clean'),
    Case('rebuild_clean', lease=True),
    Case('ecc_clean', 'ecc_halt'),
    Case('tmr_clean', 'tmr'),
    Case('ecc_data_check_repair', 'ecc_halt',
         '500001 R17\n7000001 C21:0\n13000001 R17\n8000000000 R17\n', 3, 3),
    Case('ecc_distinct_words', 'ecc_halt', '500001 R17;W0:0\n', 1, 2),
    Case('ecc_same_word_double', 'ecc_halt', '500001 R17;R18\n', 1, halt=True),
    Case('ecc_same_tick_separate_events', 'ecc_halt', '500001 R17\n500001 R18\n', 2, halt=True),
    Case('tmr_same_replica_double_and_repair', 'tmr',
         '500001 T1:21:17;T1:21:18\n7000001 T2:21:17\n13000001 R17\n', 3, 3),
    Case('tmr_distinct_bits_two_replicas', 'tmr', '500001 T1:21:17;T2:21:18\n', 1, 1),
    Case('tmr_common_mode_diagnostic', 'tmr', '500001 T1:21:17;T2:21:17\n', 1, 1),
)


def run(case, args):
    output = args.output/case.name
    command = [
        sys.executable, str(ROOT/'tools/gem5.py'), 'run', '--tree', str(args.tree),
        '--config', str(ROOT/'simulation/gem5/configs/native_study.py'), '--outdir', str(output),
        '--', '--binary', str(args.binary), '--execute', '--history-protection', case.mode,
        '--cycle-ticks', '13850', '--query-pipeline', '--single-training-port', '--max-ticks', '4000000000',
    ]
    if case.lease:
        command += ['--lease-period', '4096']
    if case.schedule:
        tape = args.output/(case.name+'.events')
        tape.write_text('# time_unit=ticks horizon=8000000000\n'+case.schedule)
        command += ['--schedule', str(tape)]
    with (args.output/(case.name+'.log')).open('x') as log:
        with subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                              start_new_session=True) as process:
            try:
                code = process.wait(timeout=args.timeout)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise
        if code:
            raise subprocess.CalledProcessError(code, command)
    native = json.loads((output/'native.json').read_text())
    termination = json.loads((output/'termination.json').read_text())
    expected_status = 'DETECTED_STOP' if case.halt else 'PASS'
    if termination['status'] != expected_status:
        raise ValueError(f'{case.name}: unexpected termination {termination}')
    if not case.halt and (output/'program.stdout').read_bytes() != EXPECTED:
        raise ValueError(f'{case.name}: incorrect checksum')
    if case.halt and (output/'program.stdout').read_bytes() == EXPECTED:
        raise ValueError(f'{case.name}: detected stop already completed the program')
    if native['applied_events'] != case.events:
        raise ValueError(f'{case.name}: expected {case.events} pre-stop events')
    with (output/'events.csv').open() as f:
        rows = list(csv.DictReader(f))
    for row, entry in zip(rows, case.schedule.splitlines()):
        requested, marks = entry.split()
        if (row['requested_tick'] != requested or row['applied_tick'] != requested or
                int(row['multiplicity']) != len(marks.split(';'))):
            raise ValueError(f'{case.name}: event ordering or width mismatch')
        before = row['bit_values_before'].split(';')
        after = row['bit_values_after'].split(';')
        if any({a,b} != {'0','1'} for a,b in zip(before, after)):
            raise ValueError(f'{case.name}: injection did not flip stored bits')
    if len(rows) != case.events:
        raise ValueError(f'{case.name}: event trace length mismatch')
    if case.mode != 'none':
        if (native['protection_repair_words'] != case.repaired_words or
                native['history_protection_halted'] != case.halt or
                bool(native['protection_due_words']) != case.halt):
            raise ValueError(f'{case.name}: repair or stop counters mismatch')
    return {'case': case.name, 'status': expected_status, 'stop_tick': native['tick'],
            'applied_events': len(rows), 'retired_pc_identity': native['retired_pc_identity'],
            'retired_instructions': native['retired_instructions'],
            'first_hash_tick': native['first_staged_capture_tick'],
            'first_hash_identity': native['first_staged_hash_identity']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--binary', type=Path, default=ROOT/'build/checksum')
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 16 or args.timeout <= 0:
        parser.error('jobs must be 1..16 and timeout must be positive')
    args.output, args.tree, args.binary = (p.resolve() for p in (args.output,args.tree,args.binary))
    if subprocess.check_output([str(args.binary)], timeout=5) != EXPECTED:
        parser.error('host checksum mismatch')
    args.output.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        results = list(pool.map(lambda case:run(case,args), CASES))
    by_name = {row['case']:row for row in results}
    reference = by_name['ordinary_clean']
    tick = reference['first_hash_tick']
    if not tick:
        raise ValueError('checksum did not exercise a staged hash capture')
    boundary_cases = (
        Case('ecc_repair_before_hash', 'ecc_halt', f'{tick} W0:0\n', 1, 1),
        Case('tmr_repair_before_hash', 'tmr', f'{tick} W0:0\n', 1, 1),
    )
    boundary_results = [run(case, args) for case in boundary_cases]
    for measured in [by_name['ecc_clean'], by_name['tmr_clean'], *boundary_results]:
        if any(measured[key] != reference[key] for key in
               ('stop_tick','retired_pc_identity','retired_instructions')):
            raise ValueError(f"{measured['case']}: protected timing or instructions changed")
    if any(row['first_hash_identity'] != reference['first_hash_identity'] for row in boundary_results):
        raise ValueError('staged hash captured a corrupt operand before repair')
    results.extend(boundary_results)
    (args.output/'DIRECTED.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
