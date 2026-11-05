"""Common raw130 source marks, single-event and two predeclared overlap regimes."""
from v5_r5_common import *
from rng_namespace import rng,descriptor
inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words'];raw=next(w['site_ids'] for w in scope if len(w['site_ids'])==130)
policies=['NATIVE','PARITY64','ECC64_RMW','BATCH_DIRECT','BATCH_STRAT16'];jobs=[];owners=[]
for wi,item in enumerate(inputs):
 A=clean_row(item['name'],'NATIVE');H=max(clean_row(item['name'],x)['cycles'] for x in policies)
 for si,scenario in enumerate(['SBU','RHO1','RHO10']):
  for n in range(4):
   master=3175480000+wi*1000000+si*10000+n;tt=rng(master,'time');kk=rng(master,'K');ll=rng(master,'location');events=[]
   if scenario=='SBU':events=[dict(tick=int(tt.integers(1,H+1))*500,sites=[raw[int(ll.integers(130))]],K=1)]
   else:
    rho=1 if scenario=='RHO1' else 10;rate=rho/A['cycles'];cycle=0.
    while True:
     cycle+=float(tt.exponential(1/rate))
     if cycle>=4*H:break
     K=1 if int(kk.integers(214))<205 else 2;start=int(ll.integers(130-K+1));events.append(dict(tick=max(1,int(round(cycle*500))),sites=raw[start:start+K],K=K))
   owner=f'R5_SOURCE.{si}.{n}';text=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events)
   owners.append(dict(program=item['name'],owner=owner,master=master,scenario=scenario,events=events,time=descriptor(master,'time'),K=descriptor(master,'K'),location=descriptor(master,'location'),
       scope='Common raw130 bits, no absent-fold pseudo-event. Conditional targeted stress, not calibrated whole-design hazard.',time_quantum_ps=1,cap_cycles=4*H))
   for ident in policies:jobs.append(make(item,ident,'SOURCE',scenario,owner,text,expected=A['instructions']))
write(OUT/'configs/SOURCE_owners.lock.json',dict(status='FROZEN_BEFORE_DISPATCH',owners=owners,
 primary_reference='NATIVE; selected legacy protection and two frozen representation families',
 planned_cases=180,refinements_remaining=0,helpful_and_unapplied_kept=True))
execute(jobs,'SOURCE',workers=8)
note('R5.SOURCE','IMPLEMENTED_CPU','180 full raw-window matched runs completed','Assess net gain, conditional impacts and overlap without rate calibration claims','Whole exposed storage, persistent task and independent evaluation')
