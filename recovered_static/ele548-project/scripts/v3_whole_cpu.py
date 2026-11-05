"""Semantic common-latent coupling for whole enumerated storage exposure."""
import argparse,json,concurrent.futures,statistics,hashlib
import numpy as np
import v3_cpu_common as runner
from v3_cpu_common import *
from rng_namespace import rng,descriptor
from continuation_statistics import abcd,fixed_program_bootstrap
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['design','evaluation'],required=True);p.add_argument('--workers',type=int,default=2);a=p.parse_args();phase=a.phase
runner.BINARY=ROOT/'third_party/gem5-costaware-v3-b/build/X86_STAGE0/gem5.opt';runner.CONFIG=ROOT/'gem5/o3_costaware_v3_B.py'
if phase=='evaluation':runner.select_final_endpoint()
primary=json.loads((OUT/f'reports/CPU_{phase.upper()}.json').read_text())
inputs=json.loads((OUT/f'configs/{phase}_inputs.lock.json').read_text())['programs']
variants=json.loads((OUT/f'configs/CPU_{phase}.runs.lock.json').read_text())['variants']
clean={(r['program'],r['id']):r for r in primary['tasks'] if r['scenario']=='zero' and r['status']=='PASS'}
assert len(clean)==len(inputs)*len(variants),'All real native-checked clean rows required'
# A mark identifies a cell by role, word, bit and replica; scheme-private ordinal IDs
# cannot couple physically different parity/queue/shadow cells.
maps={}
for i in inputs:
 for v in variants:
  m=json.loads((ROOT/clean[i['name'],v['id']]['output']/'logical_manifest.json').read_text())
  mp={('BASE',n):n for n in range(m['base_bits'])}
  for s in m['additional_sites']:
   key=(s['structure'],s['word'],s['bit'],s.get('replica',0));assert key not in mp;mp[key]=s['id']
  assert len(mp)==m['total_bits'];maps[i['name'],v['id']]=mp
union=sorted(set().union(*[set(m) for m in maps.values()]),key=lambda k:json.dumps(k))
rate=1e-6/65370;trials=5 if phase=='design' else 10;base=2425480000 if phase=='design' else 2525480000
jobs=[]
for wi,i in enumerate(inputs):
 A=clean[i['name'],'P0'];cap=4*A['cycles']
 for n in range(trials):
  master=base+wi*1000000+n;tr=rng(master,'time');lr=rng(master,'location');t=0;incidents=[]
  while True:
   t+=float(tr.exponential(1/(rate*len(union))))
   if t>=cap:break
   incidents.append((max(1,int(round(t*500))),union[int(lr.integers(len(union)))]))
  latent_hash=hashlib.sha256(json.dumps(incidents).encode()).hexdigest()
  for v in variants:
   mp=maps[i['name'],v['id']];events=[(t,mp[key]) for t,key in incidents if key in mp]
   jobs.append(dict(v,phase='B_WHOLE_'+phase,program=i['name'],input=i,U=0,owner=f'V3_WHOLE_{phase.upper()}_W{wi}_N{n}',seed=master,namespaces={r:descriptor(master,r) for r in ['time','location']},label=f"{i['name']}.whole.n{n}.{v['id']}",scenario='WHOLE_EQUAL_PER_BIT_SBU',trial=n,events_text=''.join(f'{t} {site}\n' for t,site in events),latent_schedule_sha256=latent_hash,latent_mark_count=len(incidents),absent_marks=len(incidents)-len(events),effective_rate_per_cycle=rate*len(mp),max_ticks=cap*500,expected_instructions=A['instructions'],additional_args=['--resource-mode','SHARED2','--rmw-latency','1','--rmw-ii','1']+(['--decouple-shadow'] if v.get('split') else [])))
forecast=statistics.mean(r['host_cpu_seconds'] for r in clean.values())*len(jobs)*1.5/3600
lock=OUT/f'configs/B_WHOLE_{phase}.runs.lock.json';assert not lock.exists()
write(lock,dict(status='FROZEN_BEFORE_NEW_OUTCOMES',jobs=jobs,virtual_union_cell_count=len(union),virtual_cell_keys=union,per_bit_rate_per_cycle=rate,rate_measured=False,scope='all enumerated predictor and recovery storage including finite engine; architectural/BI/pointer/timing exclusions remain explicit',coupling='Poisson on semantic union; independently retain owned roles. Same base bit incidents; private cells absent, not remapped.',forecast_core_hours=forecast))
assert forecast+used_cpu()/3600<32,'Round checkpoint; fixed plan preserved'
rows=[];report=OUT/f'reports/B_WHOLE_{phase.upper()}.json'
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
 for start in range(0,len(jobs),a.workers):
  if used_cpu()>32*3600:raise SystemExit('Round checkpoint; remaining fixed plan retained')
  for r in pool.map(runner.run_cpu,jobs[start:start+a.workers]):
   rows.append(r);write(report,dict(status='RUNNING',planned=len(jobs),completed=len(rows),tasks=rows));print(r['label'],r['status'],r.get('failure'),flush=True)
write(report,dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL_RETAINED',planned=len(jobs),completed=len(rows),tasks=rows))
by={(r['program'],r['trial'],r['id']):r for r in rows};pairs=[];failed=[]
for D in rows:
 B=by[D['program'],D['trial'],'P0'];A=clean[D['program'],'P0'];C=clean[D['program'],D['id']]
 if any(r['status']!='PASS' for r in [A,B,C,D]):failed.append(dict(owner=D['owner'],variant=D['id'],statuses=[r['status'] for r in [A,B,C,D]]));continue
 assert D['owner']==B['owner'] and D['latent_schedule_sha256']==B['latent_schedule_sha256'] and D['input_sha256']==B['input_sha256']
 assert A['instructions']==B['instructions']==C['instructions']==D['instructions']
 pairs.append(dict(program=D['program'],variant=D['id'],owner=D['owner'],**abcd(A['cycles'],B['cycles'],C['cycles'],D['cycles']),events_B=B['seu']['applied_events'],events_D=D['seu']['applied_events'],latent_schedule_sha256=D['latent_schedule_sha256']))
summary=[]
for v in variants:
 rr=[r for r in pairs if r['variant']==v['id']]
 if rr:summary.append(dict(variant=v['id'],valid_pairs=len(rr),net_pp=fixed_program_bootstrap({i['name']:[r['net_pp'] for r in rr if r['program']==i['name']] for i in inputs},iterations=10000,seed=8171026),per_program={i['name']:fixed_program_bootstrap({i['name']:[r['net_pp'] for r in rr if r['program']==i['name']]},iterations=10000,seed=8171026) for i in inputs}))
write(OUT/f'reports/B_WHOLE_{phase.upper()}_SUMMARY.json',dict(status='ACTUAL_PAIRED_ANALYSIS',summary=summary,pairs=pairs,failures=failed,runs=len(rows),failed_runs=sum(r['status']!='PASS' for r in rows),scope_lock_sha256=sha(lock),no_physical_rate_claim=True))
print('Actual whole-storage',phase,len(rows),'failed',sum(r['status']!='PASS' for r in rows),flush=True)
