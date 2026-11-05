"""Bounded finalization of already dispatched experiments; no new research jobs."""
from v5_common import ROOT,timed
import json,time,datetime,subprocess,sys
R=ROOT/'rate_state_v5/runtime_r5';F=ROOT/'rate_state_v5/results'
required=['SOURCE','WHOLE','SHORT_CONTROL','METADATA','PERSISTENT_CLEAN','PERSISTENT_FAULT','EVALUATION_V3_CLEAN','EVALUATION_V3_FAULT']
deadline=time.monotonic()+14*3600
while True:
 ready=True;states=[]
 for name in required:
  path=R/'reports'/(name+'.json')
  try:d=json.loads(path.read_text())
  except (FileNotFoundError,json.JSONDecodeError):ready=False;states.append(name+':WAIT');continue
  states.append(name+':'+d['status']+':'+str(len(d.get('tasks',[]))))
  if d['status']=='FAIL_RETAINED':raise RuntimeError('Stage failure retained: '+name)
  ready=ready and d['status'] in ['PASS','COMPLETED_WITH_FAILED_RUNS']
 if ready:break
 assert time.monotonic()<deadline,'BOUNDED_FINALIZATION_WAIT_EXPIRED'
 print(datetime.datetime.now(datetime.timezone.utc).isoformat(),' '.join(states),flush=True)
 time.sleep(55)
for script in ['v5_contracts.py','v5_lifetime_summary.py','v5_analyze_cpu.py','v5_figures.py','v5_final_reports.py','v5_final_audit.py']:
 r=timed([ROOT/'.venv/bin/python',ROOT/'scripts'/script],R/'reports'/('FINAL_'+script+'.log'),timeout=1800)
 assert r['exit_code']==0,(script,r)
print('FINAL_ANALYSIS_AND_AUDIT_PASS; package and final review remain',flush=True)
