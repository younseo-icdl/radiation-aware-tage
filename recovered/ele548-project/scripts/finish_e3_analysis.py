#!/usr/bin/env python3
"""Wait for the existing campaign; audit/render it once, never restart experiments."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'reports/e3_cpu/postprocess_status.json'


def save(status, **details):
    OUTPUT.write_text(json.dumps({'status': status, **details}, indent=2)+'\n')


def main():
    # Watch the owning shell, which advances main -> latency under set -e.
    shell_pid = int(sys.argv[1])
    phases = ['main', 'latency']
    done = []
    for phase in phases:
        path = ROOT/f'reports/E3_CPU_{phase.upper()}.json'
        while True:
            try:
                report = json.loads(path.read_text())
            except (FileNotFoundError, json.JSONDecodeError):
                report = None  # A live driver can be rewriting the JSON.
            if report and report['status'] != 'RUNNING':
                break
            try:
                os.kill(shell_pid, 0)
            except ProcessLookupError:
                # One last read handles a completed final write after the shell exits.
                try:
                    report = json.loads(path.read_text())
                except (FileNotFoundError, json.JSONDecodeError):
                    report = None
                if report and report['status'] != 'RUNNING':
                    break
                save('FAIL_DRIVER_EXITED_WITHOUT_COMPLETE_PHASE', phase=phase, completed_analyses=done)
                raise SystemExit(1)
            save('WAITING_EXISTING_CAMPAIGN', phase=phase, shell_pid=shell_pid, completed_analyses=done)
            time.sleep(30)
        process = subprocess.run([sys.executable, str(ROOT/'scripts/summarize_e3_cpu.py'), '--phase', phase], cwd=ROOT)
        if process.returncode:
            save('FAIL_PHASE_ANALYSIS', phase=phase, completed_analyses=done)
            raise SystemExit(process.returncode)
        done.append(phase)
        if report['status'] != 'PASS_FIXED_CPU_'+phase.upper():
            save('FAIL_CAMPAIGN_RETAINED_IN_AUDIT', phase=phase, completed_analyses=done)
            raise SystemExit(1)
    process = subprocess.run([sys.executable, str(ROOT/'scripts/render_e3_cpu_report.py')], cwd=ROOT)
    if process.returncode:
        save('FAIL_REPORT_RENDER', completed_analyses=done)
        raise SystemExit(process.returncode)
    save('PASS_PHASE_AUDITS_AND_CPU_REPORT', completed_analyses=done,
         final_project_evidence_review='still required; this process does not mark the goal complete')


if __name__ == '__main__':
    main()
