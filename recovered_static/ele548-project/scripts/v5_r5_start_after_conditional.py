"""Bounded ordinary experiment sequence, not a daemon or recursive agent."""
from pathlib import Path
import json,time,subprocess
ROOT=Path(__file__).resolve().parents[1];out=ROOT/'rate_state_v5/runtime_r5';deadline=time.monotonic()+90*60
print('Wait for R4 conditional batch to finish; its successor and R5 share8file-lock CPU slots.',flush=True)
while True:
 p=ROOT/'rate_state_v5/runtime/reports/A_CONDITIONAL.json'
 try:status=json.loads(p.read_text())['status']
 except (OSError,json.JSONDecodeError):status='RUNNING'
 if status=='PASS':break
 if status.startswith('FAIL'):raise RuntimeError('R4 failed; inspect preserved failures before simultaneous dispatch')
 if time.monotonic()>deadline:raise TimeoutError('Bounded wait expired; no CPU job dispatched')
 time.sleep(5)
subprocess.run([ROOT/'.venv/bin/python',ROOT/'scripts/v5_r5_freeze.py','--build','3'],cwd=ROOT,check=True)
subprocess.run([ROOT/'.venv/bin/python',ROOT/'scripts/v5_r5_gate.py'],cwd=ROOT,check=True)
subprocess.run([ROOT/'.venv/bin/python',ROOT/'scripts/v5_r5_clean.py'],cwd=ROOT,check=True)
print('R5 gate and clean screen completed; actual results available for next decision.',flush=True)
