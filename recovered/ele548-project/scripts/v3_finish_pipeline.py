"""Resume only unexecuted fixed stages after the corrected producer gate."""
import json,time,subprocess
from v3_common import *
while not (OUT/'configs/FINAL_PRODUCER.lock.json').exists():time.sleep(5)
assert json.loads((OUT/'reports/C_CPU_GATE.json').read_text())['status']=='PASS'
for name in ['B_RESOURCE','B_WHOLE_DESIGN','B_WINDOWS']:
 x=json.loads((OUT/f'reports/{name}.json').read_text());assert x['status']=='PASS'
def launch(script,args,label):
 log=OUT/'reports'/f'PIPELINE_{label}.log';assert not log.exists()
 with log.open('w') as f:r=subprocess.run([ROOT/'.venv/bin/python',ROOT/'scripts'/script]+args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError(f'{label} exit {r.returncode}; inspect {log}')
 print('Completed stage',label,flush=True)
launch('v3_freeze.py',[],'FREEZE_V2')
launch('v3_campaign.py',['--phase','evaluation','--workers','8'],'EVALUATION')
launch('v3_summarize_cpu.py',['--phase','evaluation'],'EVALUATION_ANALYSIS')
launch('v3_whole_cpu.py',['--phase','evaluation','--workers','8'],'WHOLE_EVALUATION')
while not (OUT/'reports/B_SPARSE_SUMMARY.json').exists():time.sleep(5)
launch('v3_final_audit.py',[],'FINAL_AUDIT')
launch('v3_render_final.py',[],'FINAL_REPORT')
print('FIXED_SOFTWARE_ROUND_COMPLETE; review bundle and local commit remain; no HDL',flush=True)
