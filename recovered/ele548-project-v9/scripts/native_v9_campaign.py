"""Predeclared common-source single events and augmented-storage repeated stress."""
import argparse
from native_v9_common import *
from rng_namespace import rng,descriptor

def semantic_map(manifest):
 base=[json.loads(line) for line in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
 result={'base:'+str(s['site_id']):s['site_id'] for s in base if not (manifest['direct'] and s['field']=='folded')}
 for s in manifest['additional_sites']:
  key='extra:'+':'.join(str(s[k]) for k in ['structure','word','bit','replica']);assert key not in result;result[key]=s['id']
 assert len(result)==len(set(result.values()))==manifest['total_bits'],'MANIFEST_POPULATION_MISMATCH'
 return result
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['clean','development'],required=True);phase=parser.parse_args().phase
 assert load(OUT/'configs/PRODUCER.lock.json')['status']=='PASS_NATIVE_L0_CPU_GATE_BEFORE_DEVELOPMENT'
 items=load(OUT/'configs/development_inputs.lock.json')['programs']
 if phase=='clean':
  result=execute([make(item,i,'CLEAN') for item in items for i in IDS],'CLEAN');cm={(r['program'],r['id']):r for r in result}
  for item in items:
   refrow=cm[item['name'],'U']
   for ident in IDS:
    row=cm[item['name'],ident]
    for key in ['cycles','instructions']:assert row[key]==refrow[key],('CLEAN_NATIVE_EXECUTION',item['name'],ident,key)
    for key in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']:assert row['seu'][key]==refrow['seu'][key],('CLEAN_NATIVE_STATE',item['name'],ident,key)
  write(OUT/'reports/CLEAN_ACCEPTANCE.json',dict(status='PASS_ALL_SIX_NATIVE_NORMAL_PROGRAMS',source=ref(OUT/'reports/CLEAN.json'),assumption='Inline normal check/vote/maintain costs assumed stage-fit, physical full protection timing unknown'))
  note('L0.CLEAN','Actual six-family nofault cycles/instructions/final state/RNG match for each development program','No normal scheduling confound in this assumed C0 endpoint','Freeze two fault scenarios and actual storage populations before paired development')
  return
 assert load(OUT/'reports/CLEAN_ACCEPTANCE.json')['status'].startswith('PASS')
 clean=load(OUT/'reports/CLEAN.json')['tasks'];cm={(r['program'],r['id']):r for r in clean}
 maps={ident:semantic_map(load(ROOT/cm[items[0]['name'],ident]['output']/'logical_manifest.json')) for ident in IDS}
 for item in items:
  for ident in IDS:assert maps[ident]==semantic_map(load(ROOT/cm[item['name'],ident]['output']/'logical_manifest.json'))
 union=sorted(set().union(*(set(m) for m in maps.values())));jobs=[];owners=[]
 raw=next(w['site_ids'] for w in load(ROOT/'sources/protection_scope.lock.json')['payload_words'] if len(w['site_ids'])==130)
 for wi,item in enumerate(items):
  name=item['name'];A=cm[name,'U']['cycles'];H=max(cm[name,ident]['cycles'] for ident in IDS)
  for si,scenario in enumerate(['RAW130_SINGLE_SBU','WHOLE_K1_REF_SCALE1E15']):
   for n in range(2):
    master=9415480000+wi*1000000+si*10000+n;tt,ll=rng(master,'time'),rng(master,'location');events={i:[] for i in IDS};latent=[]
    if si==0:
     tick=max(1,int(tt.integers(1,A*500+1)));age=int(ll.integers(130));site=raw[age];latent=[dict(tick=tick,K=1,raw_age=age,site=site)]
     for ident in IDS:events[ident]=[dict(tick=tick,sites=[site])]
     rate=None
    else:
     rate=(1.05e-14*20/3600*1e15)*len(union)/2e9;cycle=0.
     while True:
      cycle+=float(tt.exponential(1/rate))
      if cycle>4*H:break
      tick=max(1,int(round(cycle*500)));key=union[int(ll.integers(len(union)))];latent.append(dict(tick=tick,K=1,site_key=key))
      for ident in IDS:
       if key in maps[ident]:events[ident].append(dict(tick=tick,sites=[maps[ident][key]]))
    owner=f'V9_DEVELOPMENT.{si}.{n}'
    owners.append(dict(program=name,scenario=scenario,owner=owner,master=master,time=descriptor(master,'time'),location=descriptor(master,'location'),clock_Hz=2000000000,cycle_ticks=500,cap_cycles=4*H,lambda_union_per_cycle=rate,latent=latent,accepted=events,populations={ident:len(m) for ident,m in maps.items()},scope='development on previously seen input, K1 only; singleeventconditional versus hypothetical accelerated perbit environment'))
    for ident in IDS:
     tape=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events[ident]);job=make(item,ident,'DEVELOPMENT',scenario,owner,tape,expected=cm[name,ident]['instructions'])
     if si==1:job['tape_horizon_ticks']=4*H*500
     jobs.append(job)
 for name in ['DEVELOPMENT_maps.lock.json','DEVELOPMENT_owners.lock.json']:assert not (OUT/'configs'/name).exists(),'IMMUTABLE_FAULT_DECLARATION'
 write(OUT/'configs/DEVELOPMENT_maps.lock.json',dict(status='ACTUAL_CLEAN_MANIFESTS_BEFORE_FAULTS',maps=maps,union_size=len(union),producer=ref(OUT/'configs/PRODUCER.lock.json')))
 write(OUT/'configs/DEVELOPMENT_owners.lock.json',dict(status='FIXED_BEFORE_FAULT_DISPATCH',owners=owners,maps=ref(OUT/'configs/DEVELOPMENT_maps.lock.json'),reference_arithmetic='1.05e-14 cm2/bit *20/cm2/hour /3600 *1e15; FF transfer unknown; K1 eventrate=fliprate; common2GHz fixed clock',no_MCU_claim='No repeated CHARM MCU native evidence in this initial chunk; prior CHARM/lifetime remains separately scoped'))
 execute(jobs,'DEVELOPMENT')
 note('L0.DEVELOPMENT','All actual paired tasks are terminal; signed/zero/future and failures are retained','Analyze each program and conventional competitor before selecting candidates/domain','Use separate fresh-input owners for confirmation within remaining global budget, otherwise report exact required extension')
if __name__=='__main__':main()
