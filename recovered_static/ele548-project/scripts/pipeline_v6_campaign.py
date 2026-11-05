"""Bounded matched lookup study; no parameter tuning after holdout freeze."""
from pipeline_v6_common import *
from rng_namespace import rng,descriptor
import argparse
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['clean','pilot','freeze','evaluation_clean','evaluation_fault'],required=True);a=p.parse_args()
POLICIES=['P_REC_L1','P_DIR_L1']
def rowmap(rows):return {(r['program'],r['id']):r for r in rows}
def variant_task(item,ident,phase,scenario='zero',owner='CONTROL',event='',expected=None):
 mode='single' if ident.startswith('S_') or ident=='JOURNAL_SINGLE_L1' else 'pipeline'
 rep='direct' if '_DIR_' in ident or ident.startswith('JOURNAL') else 'recurrent'
 L=2 if ident.endswith('L2') else 1;extra=[]
 if ident=='NATIVE':mode='native'
 if ident.startswith('JOURNAL'):extra=['--journal-service','--journal-merge-undo','--undo-batch-latency','2']
 if ident=='STRAT16_PIPE_L1':rep='stratum';extra=['--tap-budget','16']
 return make(item,ident,phase,scenario,owner,event,mode,rep,L,extra,expected)
def design_inputs():
 d=json.loads((ROOT/'rate_state_v5/runtime_r5/configs/CLEAN.lock.json').read_text())
 items={r['program']:r['input'] for r in d['tasks']}
 return [items[p] for p in ['qsort_small','dijkstra_small','sha1']]
def manifest_map(clean):
 base=[json.loads(s) for s in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
 maps={}
 for ident in POLICIES:
  r=next(r for r in clean if r['id']==ident);m=json.loads((ROOT/r['output']/'logical_manifest.json').read_text())
  sites={'base:'+str(s['site_id']):s['site_id'] for s in base if not(m['direct'] and s['field']=='folded')}
  for s in m['additional_sites']:sites['extra:'+':'.join(str(s[k]) for k in ['structure','word','bit','replica'])]=s['id']
  assert len(sites)==m['total_bits'];maps[ident]=sites
 return maps
def owner_schedule(item,wi,scenario,n,cleans,master_base,identifiers):
 cm=rowmap(cleans);name=item['name'];A=cm[name,'NATIVE']['cycles'];H=max(cm[name,i]['cycles'] for i in ['NATIVE']+identifiers)
 si=0 if scenario=='SOURCE' else 1;master=master_base+wi*1000000+si*10000+n
 tt,ll,kk=rng(master,'time'),rng(master,'location'),rng(master,'K');cycle=0.;events={i:[] for i in identifiers};latent=[]
 raw=next(w['site_ids'] for w in json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words'] if len(w['site_ids'])==130)
 maps=manifest_map(cleans) if scenario=='WHOLE' else None
 universe=sorted(set().union(*(set(x) for x in maps.values()))) if maps else None
 rate=1/A if scenario=='SOURCE' else (1.05e-14*20/3600*1e15)*len(universe)/2e9
 while True:
  cycle+=float(tt.exponential(1/rate))
  if cycle>4*H:break
  tick=max(1,int(round(cycle*500)))
  if scenario=='SOURCE':
   K=1 if int(kk.integers(214))<205 else 2;start=int(ll.integers(130-K+1));sites=raw[start:start+K]
   latent.append(dict(tick=tick,K=K,sites=sites))
   for i in identifiers:events[i].append(dict(tick=tick,sites=sites))
  else:
   key=universe[int(ll.integers(len(universe)))];latent.append(dict(tick=tick,site_key=key))
   for i in identifiers:
    if key in maps[i]:events[i].append(dict(tick=tick,sites=[maps[i][key]]))
 text={i:''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events[i]) for i in identifiers}
 return text,dict(program=name,scenario=scenario,owner_index=n,master=master,time=descriptor(master,'time'),location=descriptor(master,'location'),K=descriptor(master,'K'),
  cap_cycles=4*H,clock_Hz=2000000000,cycle_ticks=500,lambda_union_or_target_per_cycle=rate,latent=latent,accepted=events,
  populations={k:len(v) for k,v in maps.items()} if maps else {'raw_source':130},
  semantic='SOURCE empirical CHARM K weights205:9 +synthetic Poisson independence; WHOLE referenceperbit×1e15 SBU with architecture thinning. Not target calibration. Future/zero/helpful marks retained.')
if a.phase=='clean':
 assert json.loads((OUT/'configs/PRODUCER.lock.json').read_text())['status'].startswith('CPU_GATE_PASS')
 oldp=ROOT/'rate_state_v5/runtime_r5/reports/CLEAN.json';oldr=json.loads(oldp.read_text())['tasks']
 ref=OUT/'configs/reference_rows.lock.json'
 if not ref.exists():write(ref,dict(status='REUSED_ACTUAL_R5_NOT_NEW_EXECUTIONS',source_report=str(oldp.relative_to(ROOT)),source_sha256=sha(oldp),rows=[r for r in oldr if r['id'] in ['NATIVE','BATCH_READ1','BATCH_STRAT16']]))
 ids=['NATIVE']+[f'{m}_{r}_L{L}' for L in [1,2] for m in ['S','P'] for r in ['REC','DIR']]+['JOURNAL_SINGLE_L1','JOURNAL_PIPE_L1','STRAT16_PIPE_L1']
 jobs=[variant_task(item,i,'CLEAN_SCREEN') for item in design_inputs() for i in ids]
 assert len(jobs)==36
 rows=execute(jobs,'CLEAN_SCREEN',workers=8);cm=rowmap(rows)
 for item in design_inputs():
  name=item['name'];r=cm[name,'NATIVE'];native=next(x for x in oldr if x['program']==name and x['id']=='NATIVE')
  for k in ['cycles','instructions']:assert r[k]==native[k],('NATIVE_FULL_PROGRAM_COMPAT',name,k)
  for L in [1,2]:
   refrow=cm[name,f'P_REC_L{L}']
   for m in ['S','P']:
    for rep in ['REC','DIR']:
     trial=cm[name,f'{m}_{rep}_L{L}']
     for k in ['cycles','instructions']:assert trial[k]==refrow[k],('COMMON_MATCHED_EQUALITY',name,L,k)
     for k in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws','audit_identity_hash']:assert trial['seu'][k]==refrow['seu'][k],('COMMON_STATE_EQUALITY',name,L,k)
  for k in ['cycles','instructions']:assert cm[name,'JOURNAL_SINGLE_L1'][k]==cm[name,'JOURNAL_PIPE_L1'][k],('JOURNAL_MATCHED_EQUALITY',name,k)
 write(OUT/'reports/CLEAN_ACCEPTANCE.json',dict(status='PASS',report_sha256=sha(OUT/'reports/CLEAN_SCREEN.json'),same_L_recurrent_direct_single_pipeline_equal=True,unchanged_R5_journal_single_pipeline_equal=True))
elif a.phase=='pilot':
 assert json.loads((OUT/'reports/CLEAN_ACCEPTANCE.json').read_text())['status']=='PASS'
 cleans=json.loads((OUT/'reports/CLEAN_SCREEN.json').read_text())['tasks'];ids=POLICIES+['S_DIR_L1'];jobs=[];owners=[]
 for wi,item in enumerate(design_inputs()):
  events,witness=owner_schedule(item,wi,'SOURCE',0,cleans,5115480000,ids);owner='PIPE_PILOT.0';witness['owner']=owner;owners.append(witness)
  for i in ids:jobs.append(variant_task(item,i,'PILOT','SOURCE',owner,events[i],rowmap(cleans)[item['name'],i]['instructions']))
 write(OUT/'configs/PILOT_owners.lock.json',dict(status='FROZEN_BEFORE_DISPATCH',owners=owners))
 execute(jobs,'PILOT',workers=2)
elif a.phase=='freeze':
 assert json.loads((OUT/'reports/PILOT.json').read_text())['status']=='PASS'
 dest=OUT/'configs/EVALUATION_PREDECLARED.lock.json';assert not dest.exists()
 items=json.loads((OUT/'configs/evaluation_inputs.lock.json').read_text())['programs']
 write(dest,dict(status='FROZEN_BEFORE_ANY_NEW_INPUT_POLICY_CPU',inputs=items,policies=POLICIES,clean_ids=['NATIVE']+POLICIES,
  scenarios=['SOURCE','WHOLE'],owners_per_program_condition=8,primary_L=1,II=1,source_backend='COMMON_SYNCHRONOUS_CONSUME_APPEND_II1_UPSTREAM_CALLBACK_ROLLBACK',
  producer_sha256=sha(OUT/'configs/PRODUCER.lock.json'),master_base=5215480000,
  inference='Exploratory paired8-owner CI; no failed cycles imputed. No tuning after freeze. Source/whole separate, same original clock/rate/RNGrole/censoring contract. No pipeline protection-cost intrinsic claim.',
  budget=dict(planned_new=170,max_new=185,projected_old=2211,global_cpu_cap=2400,global_core_h=96,new_core_h=12)))
 print('Frozen L1/II1 matched pair,3 freshinputs,2conditions,8owners;96fault tasks')
elif a.phase=='evaluation_clean':
 d=json.loads((OUT/'configs/EVALUATION_PREDECLARED.lock.json').read_text());assert sha(OUT/'configs/PRODUCER.lock.json')==d['producer_sha256']
 execute([variant_task(item,i,'EVALUATION_CLEAN') for item in d['inputs'] for i in d['clean_ids']],'EVALUATION_CLEAN',workers=8)
else:
 d=json.loads((OUT/'configs/EVALUATION_PREDECLARED.lock.json').read_text());assert sha(OUT/'configs/PRODUCER.lock.json')==d['producer_sha256']
 clean_report=json.loads((OUT/'reports/EVALUATION_CLEAN.json').read_text());assert clean_report['status']=='PASS';cleans=clean_report['tasks'];jobs=[];owners=[]
 maps=manifest_map(cleans);write(OUT/'configs/EVALUATION_maps.lock.json',dict(status='FROZEN_BEFORE_FAULT_DISPATCH',maps=maps,producer_sha256=d['producer_sha256']))
 for wi,item in enumerate(d['inputs']):
  for si,scenario in enumerate(d['scenarios']):
   for n in range(d['owners_per_program_condition']):
    events,witness=owner_schedule(item,wi,scenario,n,cleans,d['master_base'],POLICIES);owner=f'PIPE_EVAL.{si}.{n}';witness['owner']=owner;owners.append(witness)
    for i in POLICIES:jobs.append(variant_task(item,i,'EVALUATION_FAULT',scenario,owner,events[i],rowmap(cleans)[item['name'],i]['instructions']))
 write(OUT/'configs/EVALUATION_owners.lock.json',dict(status='FROZEN_BEFORE_FAULT_DISPATCH',owners=owners,
  maps_sha256=sha(OUT/'configs/EVALUATION_maps.lock.json'),predeclared_sha256=sha(OUT/'configs/EVALUATION_PREDECLARED.lock.json')))
 assert len(jobs)==96
 execute(jobs,'EVALUATION_FAULT',workers=8,allowed_failures=('FAIL_PIPELINE','pipeline queue control','inconsistent pipeline queue control','FAIL_PROTOCOL invalid bounded history pointer','gem5 has encountered a segmentation fault'))
