"""Sequential gates and bounded independent host dispatch, never old-producer mutation."""
import json,time,subprocess,concurrent.futures
from v3_common import *
report=OUT/'reports/CPU_DESIGN.json'
while True:
 d=json.loads(report.read_text())
 if d['status'] in ['PASS','FAIL_RETAINED']:break
 if d['status'].startswith('ROUND_'):raise SystemExit('Round checkpoint: development scope incomplete')
 time.sleep(5)
assert d['completed']==d['planned']
def launch(script,args,label):
 log=OUT/'reports'/f'PIPELINE_{label}.log';assert not log.exists()
 with log.open('w') as f:
  r=subprocess.run([ROOT/'.venv/bin/python',ROOT/'scripts'/script]+args,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT)
 if r.returncode:raise RuntimeError(f'{label} exit {r.returncode}; evidence {log}')
 print('Completed stage',label,flush=True)
launch('v3_summarize_cpu.py',['--phase','design'],'DESIGN_ANALYSIS')
decision('G5','Check low-cost staged recovery and decoupled H1 after representative CPU development.', ['reports/CPU_DESIGN.json','reports/CPU_DESIGN_SUMMARY.json'], {'dispatch_complete':True,'holdout_not_run':True}, 'Complete whole-population development and equal-resource/latency controls before freeze.',falsifier='Normal overhead exceeds2pct or native/protocol checks fail; no new positive result assumed.')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(launch,'v3_whole_cpu.py',['--phase','design','--workers','6'],'WHOLE_DESIGN'),pool.submit(launch,'v3_windows.py',[],'WINDOWS')]
 for f in futures:f.result()
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 futures=[pool.submit(launch,'v3_resource_sweep.py',[],'RESOURCE'),pool.submit(launch,'v3_adversarial_cpu.py',[],'ADVERSARIAL')]
 for f in futures:f.result()
launch('v3_freeze.py',[],'FREEZE')
launch('v3_campaign.py',['--phase','evaluation','--workers','8'],'EVALUATION')
launch('v3_summarize_cpu.py',['--phase','evaluation'],'EVALUATION_ANALYSIS')
launch('v3_whole_cpu.py',['--phase','evaluation','--workers','8'],'WHOLE_EVALUATION')
print('ALL_FIXED_SOFTWARE_STAGES_COMPLETE; final audit/report next, no HDL',flush=True)
