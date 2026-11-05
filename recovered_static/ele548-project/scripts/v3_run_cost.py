import json,concurrent.futures
from v3_cpu_common import *
inputs=json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text())['programs'][:2]
jobs=[]
for item in inputs:
 for remove in ['NONE','SPEC_SOURCE','COMMIT_SHADOW','FOLD_CHECK','RECOVERY','ALL']:
  jobs.append(dict(phase='A1_cost',program=item['name'],input=item,scheme='P_ED',policy='H1',k=32,C=1,U=1,cost_remove=remove,label=item['name']+'.'+remove,owner='V3_ORACLE_COST_'+item['name']+'_'+remove,scenario='zero'))
write(OUT/'configs/A1_COST.lock.json',dict(status='FROZEN_BEFORE_CPU_COST_OUTCOMES',jobs=jobs,all_are_cost_diagnostics=True,source_fold_transition_cost_overlap=True,do_not_promote_oracles=True,baseline_source_pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9'))
results=[]
def persist(status):write(OUT/'reports/A1_COST.json',dict(status=status,planned=len(jobs),completed=len(results),tasks=results,host_core_hours=sum(r.get('host_cpu_seconds') or 0 for r in results)/3600))
persist('RUNNING')
first=[j for j in jobs if j['cost_remove']=='NONE'];rest=[j for j in jobs if j['cost_remove']!='NONE']
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(run_cpu,first):
  results.append(r);persist('RUNNING');print(r['label'],r['status'],r.get('failure'),flush=True)
 if any(r['status']!='PASS' for r in results):
  persist('FAIL_INITIAL_CPU_GATE_RETAINED');raise SystemExit('First real clean gate failed; remaining cost jobs not dispatched')
 for r in pool.map(run_cpu,rest):
  results.append(r);persist('RUNNING');print(r['label'],r['status'],r.get('failure'),flush=True)
persist('PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED')
assert all(r['status']=='PASS' for r in results)
print('PASS 12 actualCPU cost-only diagnostics; not production results')
