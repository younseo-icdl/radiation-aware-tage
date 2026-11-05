"""Actual same-process task repetitions; native stdout verified for every R."""
from v5_r5_common import *
from rng_namespace import rng,descriptor
import argparse
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['clean','fault'],required=True);a=p.parse_args()
items=json.loads((OLD/'configs/persistent_inputs.lock.json').read_text())['programs']
variants=['NATIVE','FINITE0','PARITY64','ECC64_RMW','BATCH_DIRECT']
jobs=[];owners=[]
if a.phase=='clean':
 for item in sorted(items,key=lambda x:(x['repetitions'],x['name'])):
  for ident in variants:
   t=make(item,ident,'PERSISTENT_CLEAN',f"R{item['repetitions']}",'PERSIST_CLEAN')
   t['repetitions']=item['repetitions'];t['max_ticks']=2_000_000_000_000;jobs.append(t)
 execute(jobs,'PERSISTENT_CLEAN',workers=8,pilot_first_batch=2)
else:
 clean=json.loads((OUT/'reports/PERSISTENT_CLEAN.json').read_text())['tasks']
 def baseline(name,ident,R):return next(x for x in clean if x['program']==name and x['id']==ident and x['repetitions']==R)
 scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words'];raw=next(w['site_ids'] for w in scope if len(w['site_ids'])==130)
 for wi,name in enumerate(['qsort_small','dijkstra_small','sha1']):
  H=baseline(name,'FINITE0',1)['cycles']
  for n in range(2):
   master=3205480000+wi*1000000+n;tt=rng(master,'time');ll=rng(master,'location');tick=int(tt.integers(int(.2*H),int(.4*H)))*500;site=raw[int(ll.integers(len(raw)))];owner=f'PERSIST.{n}'
   owners.append(dict(program=name,owner=owner,master=master,tick=tick,site=site,time=descriptor(master,'time'),location=descriptor(master,'location'),
       policy='One common raw event early in first task. Same owner across R is correlated, not independent repetitions.'))
   for R in [1,2,8,32]:
    item=next(x for x in items if x['name']==name and x['repetitions']==R)
    for ident in ['FINITE0','PARITY64','ECC64_RMW','BATCH_DIRECT']:
     t=make(item,ident,'PERSISTENT_FAULT',f'RAW_R{R}',owner,f'{tick} {site}\n',expected=baseline(name,ident,R)['instructions']);t['repetitions']=R;t['max_ticks']=2_000_000_000_000;jobs.append(t)
 write(OUT/'configs/PERSISTENT_owners.lock.json',dict(status='FROZEN_BEFORE_DISPATCH',owners=owners,
     cold_reset_comparator='Derived sum: one measured R1 fault task plus R-1 measured R1 clean launches. This resets CPU/cache/allocator as well as BPU, not an isolated predictor-reset CPU experiment.',
     causal_predictor_only_control='C++ repeated real trace segment reset/retain diagnostic, separately labeled. No months/mission extrapolation.'))
 execute(jobs,'PERSISTENT_FAULT',workers=8)
note('A.PERSISTENT.'+a.phase,'IMPLEMENTED_CPU',f'{len(jobs)} actual repeated-task runs; output complete and native checked',
     'Compare retained-state damage versus explicitly qualified cold-launch surrogate','Rate/state horizon synthesis and held-out evaluation')
