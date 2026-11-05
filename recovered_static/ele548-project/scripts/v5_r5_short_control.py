"""Mandatory short-history control under a common age0..31 source attack."""
from v5_r5_common import *
from rng_namespace import rng,descriptor
items=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
raw=next(w['site_ids'] for w in json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words'] if len(w['site_ids'])==130)[:32]
ids=['NATIVE','SHORT32','BATCH_DIRECT','BATCH_STRAT16'];jobs=[];owners=[]
for wi,item in enumerate(items):
 A=clean_row(item['name'],'NATIVE');H=max(clean_row(item['name'],x)['cycles'] for x in ids)
 for si,scenario in enumerate(['SBU_RAW32','CHARM_RHO1_RAW32']):
  for n in range(4):
   master=3615480000+wi*1000000+si*10000+n;tt=rng(master,'time');ll=rng(master,'location');kk=rng(master,'K');events=[]
   if not si:events=[dict(tick=int(tt.integers(1,H+1))*500,sites=[raw[int(ll.integers(32))]])]
   else:
    cycle=0.
    while True:
     cycle+=float(tt.exponential(A['cycles']))
     if cycle>4*H:break
     K=1 if int(kk.integers(214))<205 else 2;start=int(ll.integers(32-K+1));events.append(dict(tick=max(1,int(round(cycle*500))),sites=raw[start:start+K]))
   owner=f'SHORT_CONTROL.{si}.{n}';text=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events)
   owners.append(dict(program=item['name'],owner=owner,master=master,scenario=scenario,events=events,
      time=descriptor(master,'time'),location=descriptor(master,'location'),K=descriptor(master,'K'),
      scope='Conditional common raw ages0..31, not uniform full130 or whole population. SHORT32 retained tables/provider/training; min2/max32 geometry changes.'))
   for ident in ids:jobs.append(make(item,ident,'SHORT_CONTROL',scenario,owner,text,expected=A['instructions']))
write(OUT/'configs/SHORT_CONTROL_owners.lock.json',dict(status='FROZEN_BEFORE_DISPATCH',owners=owners,planned=96,refinement=False))
execute(jobs,'SHORT_CONTROL',workers=8)
