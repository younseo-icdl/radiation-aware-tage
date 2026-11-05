"""Sequential continuation; each command is bounded and logs an explicit gate."""
import time,sys,subprocess,json
from continuation_common import *
path=OUT/'reports/G4_CPU_DESIGN_V2.json';start=time.monotonic()
while True:
 if path.exists():
  x=json.loads(path.read_text())
  if x['status']=='PASS':break
  if x['status'].startswith('FAIL'):raise SystemExit('Design failed; no dependent work started')
 if time.monotonic()-start>10800:raise SystemExit('Design wait bound reached; inspect ongoing explicit session')
 time.sleep(10)
commands=[
 ['scripts/summarize_continuation_cpu.py','--phase','design'],
 ['scripts/freeze_continuation_cpu.py'],
 ['scripts/run_continuation_models.py'],
 ['scripts/run_continuation_cpu_v2.py','--phase','holdout'],
 ['scripts/summarize_continuation_cpu.py','--phase','holdout']]
for i,cmd in enumerate(commands):
 if budget_charge_seconds()>=32*3600:raise SystemExit('Budget exhausted; no further job dispatched')
 with (OUT/f'reports/PIPELINE_STEP_{i}.log').open('w') as f:
  result=subprocess.run([ROOT/'.venv/bin/python']+cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 if result.returncode:raise SystemExit(f'Blocked/failed step{i}; see raw log; dependent commands not run')
 print('PASS pipeline step',i,cmd,flush=True)
print('PASS G4 design and G5 primary/source experiments; G6 analysis and packet pending',flush=True)
