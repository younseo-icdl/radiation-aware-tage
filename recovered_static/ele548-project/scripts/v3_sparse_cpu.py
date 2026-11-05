"""Fixed sparse rate sensitivity; all rows executed, including no-event owners."""
import json,concurrent.futures,statistics
import numpy as np
import v3_cpu_common as runner
from v3_cpu_common import *
from rng_namespace import rng,descriptor
from continuation_statistics import abcd,fixed_program_bootstrap
runner.BINARY=ROOT/'third_party/gem5-costaware-v3-b/build/X86_STAGE0/gem5.opt';runner.CONFIG=ROOT/'gem5/o3_costaware_v3_B.py'
runner.select_final_endpoint()
freeze=json.loads((OUT/'configs/CANDIDATE_SPEC.lock.json').read_text());variants=freeze['variants']
primary=json.loads((OUT/'reports/CPU_EVALUATION.json').read_text());assert primary['status'] in ['PASS','FAIL_RETAINED']
inputs=json.loads((OUT/'configs/evaluation_inputs.lock.json').read_text())['programs'];clean={(r['program'],r['id']):r for r in primary['tasks'] if r['scenario']=='zero' and r['status']=='PASS'}
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());words=[w['site_ids'] for w in scope['payload_words']];ends=np.cumsum([len(w) for w in words]);jobs=[]
for wi,i in enumerate(inputs):
 A=clean[i['name'],'P0'];cap=4*A['cycles']
 for n in range(10):
  master=2535480000+wi*1000000+n;tr=rng(master,'time');kr=rng(master,'K');lr=rng(master,'location');t=0;events=[]
  while True:
   t+=float(tr.exponential(1e8))
   if t>=cap:break
   K=1 if int(kr.integers(214))<205 else 2;word=words[int(np.searchsorted(ends,int(lr.integers(346)),side='right'))];start=int(lr.integers(len(word)-K+1));events.append((max(1,int(round(t*500))),word[start:start+K]))
  event_text=''.join(str(t)+' '+ ';'.join(map(str,ids))+'\n' for t,ids in events)
  for v in variants:jobs.append(dict(v,phase='B_SPARSE',program=i['name'],input=i,U=0,owner=f'V3_SPARSE_W{wi}_N{n}',seed=master,namespaces={r:descriptor(master,r) for r in ['time','K','location']},scenario='SPARSE_CHARM_K_1e8',trial=n,label=f"{i['name']}.sparse.n{n}.{v['id']}",events_text=event_text,max_ticks=cap*500,expected_instructions=A['instructions'],additional_args=['--resource-mode','SHARED2','--rmw-latency','1','--rmw-ii','1']+(['--decouple-shadow'] if v.get('split') else [])))
forecast=statistics.mean(r['host_cpu_seconds'] for r in clean.values())*len(jobs)*1.5/3600
write(OUT/'configs/B_SPARSE.lock.json',dict(status='FROZEN_BEFORE_NEW_SPARSE_OUTCOMES',jobs=jobs,rate_per_cycle=1e-8,rate_measured=False,owners_per_program=10,no_tuning_after_primary_evaluation=True,predeclared_in='configs/sensitivity_predeclared.lock.json',forecast_core_hours=forecast))
assert forecast+used_cpu()/3600<32,'Round checkpoint; fixed sparse plan retained without sample reduction'
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
 for start in range(0,len(jobs),8):
  if used_cpu()>32*3600:raise SystemExit('Round checkpoint; remaining plan retained')
  for r in pool.map(runner.run_cpu,jobs[start:start+8]):rows.append(r);write(OUT/'reports/B_SPARSE.json',dict(status='RUNNING',planned=len(jobs),completed=len(rows),tasks=rows));print(r['label'],r['status'],r.get('failure'),flush=True)
write(OUT/'reports/B_SPARSE.json',dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL_RETAINED',planned=len(jobs),completed=len(rows),tasks=rows))
by={(r['program'],r['trial'],r['id']):r for r in rows};pairs=[];failed=[]
for D in rows:
 B=by[D['program'],D['trial'],'P0'];A=clean[D['program'],'P0'];C=clean[D['program'],D['id']]
 if any(r['status']!='PASS' for r in [A,B,C,D]):failed.append(dict(owner=D['owner'],variant=D['id'],statuses=[r['status'] for r in [A,B,C,D]]));continue
 assert B['owner']==D['owner'] and B['schedule_sha256']==D['schedule_sha256'] and A['instructions']==B['instructions']==C['instructions']==D['instructions']
 pairs.append(dict(program=D['program'],variant=D['id'],owner=D['owner'],**abcd(A['cycles'],B['cycles'],C['cycles'],D['cycles']),events_B=B['seu']['applied_events'],events_D=D['seu']['applied_events']))
summary=[]
for v in variants:
 rr=[r for r in pairs if r['variant']==v['id']]
 if rr:summary.append(dict(variant=v['id'],valid_pairs=len(rr),no_event_pairs=sum(r['events_B']==r['events_D']==0 for r in rr),net_pp=fixed_program_bootstrap({i['name']:[r['net_pp'] for r in rr if r['program']==i['name']] for i in inputs},iterations=10000,seed=8171026),per_program={i['name']:fixed_program_bootstrap({i['name']:[r['net_pp'] for r in rr if r['program']==i['name']]},iterations=10000,seed=8171026) for i in inputs}))
write(OUT/'reports/B_SPARSE_SUMMARY.json',dict(status='ACTUAL_PAIRED_ANALYSIS',summary=summary,pairs=pairs,failures=failed,runs=len(rows),failed_runs=sum(r['status']!='PASS' for r in rows),no_event_replicates='Independent event owners may have identical deterministic CPU outputs; not independent clean-performance samples or workloads.'))
print('Actual sparse',len(rows),'failures',sum(r['status']!='PASS' for r in rows))
