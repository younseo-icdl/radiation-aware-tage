import time,subprocess,json
from continuation_common import *
start=time.monotonic()
while True:
 p=OUT/'reports/CPU_HOLDOUT_SUMMARY.json'
 if p.exists() and json.loads(p.read_text()).get('status')=='PASS_FIXED_SCOPE_PAIRED_ANALYSIS':break
 if time.monotonic()-start>21600:raise SystemExit('Primary holdout wait limit reached; no extra jobs started')
 time.sleep(10)
with (OUT/'reports/EXTRA_CPU_RUNNER.log').open('w') as f:r=subprocess.run([ROOT/'.venv/bin/python','scripts/run_continuation_extra_cpu.py'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit('Extra source/exposure stage failed; no final report rendered')
with (OUT/'reports/G6_RENDER.log').open('w') as f:r=subprocess.run([ROOT/'.venv/bin/python','scripts/render_continuation_final.py'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
if r.returncode:raise SystemExit('Final report rendering failed')
print('PASS G5 extra and G6 provisional render; human root visual/audit/packet remaining')
