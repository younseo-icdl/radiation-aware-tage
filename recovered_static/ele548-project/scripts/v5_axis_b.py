"""Matched raw source events; deleted fold cells are never fake no-op events."""
from v5_variants import *
from rng_namespace import rng,descriptor
import math
inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
manifest=[json.loads(x) for x in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
raw=[s['site_id'] for s in manifest if s['field']=='raw_path' and s['bank']==0]
jobs=[];owners=[]
for wi,item in enumerate(inputs):
 clean=clean_row(item['name'],'NATIVE');H=clean['cycles']
 for si,scenario in enumerate(['SBU_RAW','CHARM_RAW']):
  for n in range(4):
   master=3175480000+wi*1000000+si*10000+n;tt=rng(master,'time');kk=rng(master,'K');ll=rng(master,'location');events=[]
   if scenario=='SBU_RAW':
    cycle=int(tt.integers(int(.1*H),int(.8*H)));events=[dict(tick=cycle*500,sites=[raw[int(ll.integers(32))]],K=1)]
   else:
    cycle=0.
    while True:
     cycle+=float(tt.exponential(1e6))
     if cycle>4*H:break
     K=1 if int(kk.integers(214))<205 else 2;start=int(ll.integers(32-K+1));events.append(dict(tick=max(1,int(round(cycle*500))),sites=raw[start:start+K],K=K))
   text=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events);owner=f'B.{si}.{n}'
   owners.append(dict(program=item['name'],owner=owner,master=master,scenario=scenario,events=events,
       time=descriptor(master,'time'),K=descriptor(master,'K'),location=descriptor(master,'location'),
       scope='common raw ages0..31 for all structures, including short32; conditional stress, not whole exposure'))
   for ident in ['NATIVE','DIRECT_ISO','DIRECT_J0','STRAT16','SHORT32']:
    jobs.append(make(item,ident,'B_CONDITIONAL',scenario,owner,text,expected=clean['instructions']))
write(OUT/'configs/B_owners.lock.json',dict(status='FROZEN_BEFORE_DISPATCH',owners=owners,
    point_selection='At most2 new families (exact direct, sparse). Stratum16 chosen by declared one-time trace refinement, short32 mandatory control; no CPU outcome-based new tap change.'))
execute(jobs,'B_CONDITIONAL',workers=8)
note('B.CPU','IMPLEMENTED_CPU',f'{len(jobs)} raw matched-event CPU runs','Compare absolute cycles against native and short-history','Select at most2 candidates or reject based on predeclared clean/gain conditions')
