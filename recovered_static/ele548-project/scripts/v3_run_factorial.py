import json,concurrent.futures
from v3_cpu_common import *
inputs=json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text())['programs'][:2]
jobs=[]
for item in inputs:
 for k in [1,64]:
  for full in [False,True]:
   for U in [0,1]:
    label=item['name']+'.k'+str(k)+('.FULL' if full else '.INC')+'.U'+str(U)
    jobs.append(dict(phase='A2_factorial',program=item['name'],input=item,scheme='P_ED',policy='N1',k=k,C=1,U=U,full_delta=full,label=label,owner='V3_DEV_A2_'+item['name'],scenario='zero'))
write(OUT/'configs/A2_FACTORIAL.lock.json',dict(status='FROZEN_BEFORE_NEW_FACTORIAL_CPU_OUTCOMES',jobs=jobs,no_backend_latency_assumption_difference=True,old_inputs_are_development=True))
results=[]
def persist(s):write(OUT/'reports/A2_FACTORIAL.json',dict(status=s,planned=len(jobs),completed=len(results),tasks=results))
persist('RUNNING')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(run_cpu,jobs):results.append(r);persist('RUNNING');print(r['label'],r['status'],r.get('failure'),flush=True)
persist('PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED')
assert all(r['status']=='PASS' for r in results)
print('PASS 16 real O3 full-delta/incremental k/resource factorial runs')
