#!/usr/bin/env python3
"""Bounded O3 regression: checksum output, finite transport, and logical upsets."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = b'checksum: 2bf45f80b1c37877\n'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tree', type=Path, default=ROOT/'build/gem5')
    parser.add_argument('--binary', type=Path, default=ROOT/'build/checksum')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--jobs', type=int, default=4)
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    if not 1 <= args.jobs <= 32 or args.timeout <= 0:
        parser.error('jobs must be 1..32 and timeout must be positive')
    if args.output.exists():
        parser.error('output exists; choose a fresh validation directory')
    args.output = args.output.resolve()
    args.binary = args.binary.resolve()
    args.tree = args.tree.resolve()
    if subprocess.check_output([str(args.binary)], timeout=5) != EXPECTED:
        parser.error('native checksum mismatch')
    args.output.mkdir(parents=True)

    def run(case):
        name, options = case
        output = args.output/name
        command = [sys.executable, str(ROOT/'tools/gem5.py'), 'run', '--tree', str(args.tree),
                   '--outdir', str(output), '--', '--binary', str(args.binary), '--execute',
                   '--max-ticks', '1000000000'] + options
        record = {'case': name, 'status': 'FAIL'}
        try:
            with (args.output/(name+'.log')).open('w') as log:
                process = subprocess.Popen(command, cwd=str(ROOT), stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    code = process.wait(timeout=args.timeout)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGTERM)
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                    raise RuntimeError('timeout; simulator process group terminated')
            if code:
                raise RuntimeError('simulator exit code {}'.format(code))
            if (output/'program.stdout').read_bytes() != EXPECTED:
                raise RuntimeError('program output mismatch')
            if name != 'native':
                state = json.loads((output/'seu.json').read_text())
                termination = json.loads((output/'termination.json').read_text())
                if not (state['conserved'] and state['protection_pipeline_drained'] and
                        termination['status'] == 'PASS'):
                    raise RuntimeError('transport conservation or helper drain failed')
                if name.startswith('fault-') or name == 'metadata':
                    if state['applied_events'] != 3:
                        raise RuntimeError('fixed events were not all applied')
                    if name in ('fault-P_ECC', 'fault-P_TMR') and state['protection_corrected'] < 3:
                        raise RuntimeError('single-error correction not observed')
                    if name == 'fault-P_ED' and state['protection_resets'] != 3:
                        raise RuntimeError('parity exclude/relearn not observed')
                    if name == 'metadata' and state['metadata_repairs'] < 3:
                        raise RuntimeError('metadata repair not observed')
            record['status'] = 'PASS'
        except (OSError, ValueError, KeyError, RuntimeError) as error:
            record['error'] = str(error)
        return record

    def batch(cases):
        with ThreadPoolExecutor(max_workers=args.jobs) as pool:
            results = list(pool.map(run, cases))
        for result in results:
            print(json.dumps(result), flush=True)
        return all(result['status'] == 'PASS' for result in results)

    clean = [('native', ['--model', 'native']), ('P0', []),
             ('P_ED', ['--scheme', 'P_ED']), ('P_ECC', ['--scheme', 'P_ECC']),
             ('P_TMR', ['--scheme', 'P_TMR']),
             ('periodic', ['--scheme', 'P_ED', '--inspection-interval', '64']),
             ('direct', ['--representation', 'direct']),
             ('L2', ['--query-latency', '2', '--update-latency', '2']),
             ('early', ['--early-unconditional'])]
    if not batch(clean):
        return 1
    source = args.output/'source.events'
    source.write_text('# time_unit=ticks\n500001 R17\n7000001 W0:0\n13000001 W22:3\n')
    manifest = json.loads((args.output/'P_ECC/logical_manifest.json').read_text())
    regions = {region['name']: region for region in manifest['regions']}
    metadata = args.output/'metadata.events'
    sites = [(500001, 'controller_mirrored_SECDED'), (7000001, 'command_metadata_0'),
             (13000001, 'ordering_mirrored_SECDED')]
    metadata.write_text('# time_unit=ticks\n' + ''.join(
        '{} {}\n'.format(tick, regions[name]['start']) for tick, name in sites))
    faults = [('fault-'+scheme, ['--scheme', scheme, '--schedule', str(source)])
              for scheme in ('P0', 'P_ED', 'P_ECC', 'P_TMR')]
    faults += [('metadata', ['--scheme', 'P_ECC', '--schedule', str(metadata)])]
    return 0 if batch(faults) else 1


if __name__ == '__main__':
    sys.exit(main())
