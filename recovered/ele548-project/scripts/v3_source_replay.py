"""New implementations on frozen, already-seen source patterns; not new holdout."""
import json,csv,concurrent.futures
from v3_common import *
prior=ROOT/'continuation/runtime/configs/source_robustness.lock.json';old=json.loads(prior.read_text())
variants=[dict(id='P0',scheme='P0',policy='LEGACY',k=0),dict(id='N1',scheme='P_ED',policy='N1',k=64),dict(id='V3_P',scheme='P_ED',policy='STAGED',k=64),dict(id='H1_FUNCTIONAL_REFERENCE',scheme='P_ED',policy='H1',k=32)]
jobs=[]
for t in old['jobs']:
 if t['id']!='P0':continue
 original=t['command'];assert sha(original[1])==t['input_sha256'] and sha(original[5])==t['event_schedule_sha256']
 for v in variants:
  prefix=OUT/'reports/B_source_replay'/f"{t['workload']}.{t['scenario']}.n{t['trial']}.{v['id']}"
  cmd=[ROOT/'build/v3_B_scheduled',original[1],original[2],original[3],v['scheme'],original[5],t['scenario'],prefix,str(v['k']),v['policy'],'INC','REBUILD']
  jobs.append(dict(v,workload=t['workload'],scenario=t['scenario'],family=t['family'],trial=t['trial'],owner='V3_DEV_REPLAY_'+t['owner'],prior_owner=t['owner'],historical_seen_input=True,historical_seen_event_owner=True,input_sha256=t['input_sha256'],event_schedule_sha256=t['event_schedule_sha256'],events=t['events'],source_contract=t.get('extra'),output=str(prefix.relative_to(ROOT)),command=list(map(str,cmd))))
write(OUT/'configs/B_SOURCE_REPLAY.lock.json',dict(status='FROZEN_BEFORE_RUN',jobs=jobs,prior_plan_sha256=sha(prior),novel_source_generalization=False,D_note='H1 synchronous functional reference; actual asynchronous D CPU evidence separate'))
def run(t):
 r=timed(t['command'],ROOT/(t['output']+'.log'));r.update(t);r['status']='FAIL_EXECUTION'
 if r['exit_code']==0:
  f=ROOT/(t['output']+'.csv');m=list(csv.DictReader(f.open()));assert len(m)==1 and m[0]['status']=='PASS';assert int(m[0]['event_count'])==t['events'];assert int(m[0]['net'])==int(m[0]['harm'])-int(m[0]['help']);r.update(status='PASS',metrics=m[0],CSV_sha256=sha(f))
 return r
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(run,jobs):
  results.append(r);write(OUT/'reports/B_SOURCE_REPLAY.json',dict(status='RUNNING',planned=len(jobs),completed=len(results),tasks=results))
write(OUT/'reports/B_SOURCE_REPLAY.json',dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED',planned=len(jobs),completed=len(results),tasks=results,binary_sha256=sha(ROOT/'build/v3_B_scheduled')))
print('Actual seen-source CPP replay',len(results),'failed',sum(r['status']!='PASS' for r in results),flush=True)
