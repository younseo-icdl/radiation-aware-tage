"""Conditional single-event strata, then rate stress; no rare empty-run brute force."""
from v5_variants import *
from rng_namespace import rng,descriptor
import argparse
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['conditional','stress'],required=True);a=p.parse_args()
inputs=json.loads((ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json').read_text())['programs']
manifest=[json.loads(x) for x in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
jobs=[];owners=[]
if a.phase=='conditional':
 for wi,item in enumerate(inputs):
  clean=clean_row(item['name'],'FINITE0');H=max(clean_row(item['name'],ident)['cycles'] for ident in ['FINITE0','PARITY64','ECC64_RMW','TMR'])
  for fi,field in enumerate(['raw','path','fold','table']):
   population=[s['site_id'] for s in manifest if (field=='raw' and s['field']=='raw_path' and s['bank']==0) or (field=='path' and s['field']=='raw_path' and s['bank']==1) or (field=='fold' and s['field']=='folded') or (field=='table' and s['field'] in ['ctr','tag','u','bimodal'])]
   for n in range(8):
    master=3165480000+wi*1000000+fi*10000+n
    loc=rng(master,'location');time=rng(master,'time')
    cycle=int(time.integers(1,H+1));site=population[int(loc.integers(len(population)))];event=f'{cycle*500} {site}\n';owner=f'A.{fi}.{n}'
    owners.append(dict(program=item['name'],field=field,owner=owner,master=master,time=descriptor(master,'time'),location=descriptor(master,'location'),cycle=cycle,site=site,
        time_contract='uniform physical-cycle interval 1..max-policy-clean-duration; after-end scheduled events retained as unapplied/no-effect. Fixed common window, not calibrated rate' , common_horizon_cycles=H,stratum_bits=len(population)))
    for ident in ['FINITE0','PARITY64','ECC64_RMW','TMR']:
     jobs.append(make(item,ident,'A_CONDITIONAL',field,owner,event,expected=clean['instructions']))
else:
 scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words']
 for wi,item in enumerate(inputs):
  clean=clean_row(item['name'],'FINITE0');H=clean['cycles']
  for ri,rho in enumerate([.1,1,10]):
   for n in range(6):
    master=3185480000+wi*1000000+ri*10000+n;tt=rng(master,'time');kk=rng(master,'K');ll=rng(master,'location')
    rate=rho/H;cycle=0.;lines=[];events=[]
    while True:
     cycle+=float(tt.exponential(1/rate))
     if cycle>4*H:break
     K=1 if int(kk.integers(214))<205 else 2
     ends=list(__import__('itertools').accumulate(len(w['site_ids']) for w in scope));w=scope[__import__('bisect').bisect_right(ends,int(ll.integers(346)))];start=int(ll.integers(len(w['site_ids'])-K+1))
     ids=w['site_ids'][start:start+K];at=max(1,int(round(cycle*500)))
     lines.append(str(at)+' '+';'.join(map(str,ids))+'\n');events.append(dict(tick=at,K=K,sites=ids))
    owner=f'RATE.{ri}.{n}';owners.append(dict(program=item['name'],owner=owner,master=master,rho=rho,
        rate_event_per_cycle=rate,rate_event_per_second=rate*2e9,time=descriptor(master,'time'),K=descriptor(master,'K'),location=descriptor(master,'location'),events=events,
        classification='ACCELERATED_TARGETED_STRESS; benchmark-specific rho, not common physical environment',K_contract='Existing contract: CHARM205:9; word weighted by payload width, then uniform valid K-bit span; continuous arrival rounded to1ps tick, not compressed; Poisson timing independently assumed',end_schedule_censor_cycles=4*H))
    for ident in ['FINITE0','PARITY64','ECC64_RMW']:
     jobs.append(make(item,ident,'A_STRESS',f'rho{rho}',owner,''.join(lines),expected=clean['instructions']))
write(OUT/'configs'/f'A_{a.phase}_owners.lock.json',dict(status='FROZEN_BEFORE_DISPATCH',owners=owners,
    timing='Schedule horizon4A; applied/future event counts follow actual execution duration. helpful/zero effects retained.'))
execute(jobs,'A_'+a.phase.upper(),workers=8)
note('A.'+a.phase,'IMPLEMENTED_CPU',f'{len(jobs)} native-checked matched CPU runs completed','Compute A/B/C/D, conditional rate surrogate and event-overlap limits','Persistent state and independent owners')
