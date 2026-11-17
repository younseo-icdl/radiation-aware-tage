#!/usr/bin/env python3
"""Bounded own-clean and exposed-counter gates for base headroom controls."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = b'checksum: 2bf45f80b1c37877\n'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tree', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--native-reference', type=Path, required=True, help='native.json from native checksum')
    a = p.parse_args()
    if a.output.exists():
        p.error('output exists; choose a fresh directory')
    a.output = a.output.resolve()
    a.output.mkdir(parents=True)
    reference = json.loads(a.native_reference.read_text())
    cases = [('forced', 'BASE_FORCED', False), ('minimal', 'BASE_MIN', False),
             ('minimal-fault', 'BASE_MIN', True), ('native-fault', 'U_NATIVE', True)]

    def run(case):
        name, model, fault = case
        out = a.output/name
        cmd = [sys.executable, str(ROOT/'tools/gem5.py'), 'run', '--tree', str(a.tree.resolve()),
               '--config', str(ROOT/'simulation/gem5/configs/headroom.py'), '--outdir', str(out),
               '--', '--binary', str(ROOT/'build/checksum'), '--model', model,
               '--max-ticks', '1000000000']
        if fault:
            cmd += ['--fault-tick', '500001', '--fault-site', '17']
        row = {'case': name, 'status': 'FAIL', 'command': cmd}
        try:
            with (a.output/(name+'.log')).open('x') as log:
                x = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=120)
            assert x.returncode == 0
            assert (out/'program.stdout').read_bytes() == EXPECTED
            state = json.loads((out/'native.json').read_text())
            row['state'] = state
            assert json.loads((out/'termination.json').read_text())['status'] == 'PASS'
            assert state['applied_events'] == int(fault)
            for field in ('retired_ops', 'retired_instructions', 'retired_pc_identity'):
                assert state[field] == reference[field]
            if model == 'BASE_MIN':
                assert state['logical_counter_bits'] == 10240
                assert state['history_fold_tagged_chooser_state'] is False
            if model == 'BASE_FORCED':
                assert state['prediction_output_forced_base'] is True
            row['status'] = 'PASS'
        except (OSError, ValueError, AssertionError, subprocess.TimeoutExpired) as error:
            row['error'] = type(error).__name__+': '+str(error)
        return row

    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(run, cases))
    (a.output/'audit.json').write_text(json.dumps(rows, indent=2)+'\n')
    for row in rows:
        print(json.dumps({k: v for k, v in row.items() if k not in ('state', 'command')}))
    return 0 if all(x['status'] == 'PASS' for x in rows) else 1


if __name__ == '__main__':
    sys.exit(main())
