#!/usr/bin/env python3
"""One repeated run verifies recorded schedule and paired impact determinism."""
import csv
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
run = 'SHORT-INT-1_M1_CHARM_6T_r3_s0'
outdir = root / 'reports/repeated_pilot'
existing = list(csv.DictReader((outdir / (run + '.csv')).open()))[0]
output, events = outdir / 'repeat_check.csv', outdir / 'repeat_check.events.csv'
command = [str(root / 'build/repeated'), str(root / 'workloads/derived/SHORT-INT-1.branches'),
           existing['event_rate_per_conditional_branch'], existing['time_seed'],
           existing['k_seed'], existing['location_seed'], '205', '9', 'M1_CHARM_6T',
           str(output), str(events)]
with (outdir / 'repeat_check.log').open('w') as f:
    subprocess.run(command, cwd=root, check=True, stdout=f, stderr=subprocess.STDOUT, timeout=30)
repeated = list(csv.DictReader(output.open()))[0]
ignored = {'trial_wall_seconds', 'peak_rss_kib'}
assert {k: v for k, v in existing.items() if k not in ignored} == {k: v for k, v in repeated.items() if k not in ignored}
assert events.read_bytes() == (outdir / (run + '.events.csv')).read_bytes()
result = {'status': 'PASS_EXACT_SCHEDULE_AND_ALL_IMPACT_COUNTS', 'base_run': run,
          'additional_runs': 1, 'excluded_machine_metrics': sorted(ignored)}
(root / 'reports/REPEATED_REGRESSION.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
