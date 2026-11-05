"""V7: fixed-input/tape replication, then disjoint owners on the augmented manifest."""
from pipeline_v7_common import *
from rng_namespace import rng,descriptor
import argparse,hashlib
V6=ROOT/'rate_state_v5_pipeline/runtime'
POLICIES=['P_REC_L1','P_DIR_L1']
SCREEN_IDS=['NATIVE']+[f'{m}_{r}_L{L}' for L in [1,2] for m in ['S','P'] for r in ['REC','DIR']]+['JOURNAL_SINGLE_L1','JOURNAL_PIPE_L1','STRAT16_PIPE_L1']
def load(path):return json.loads(path.read_text())
def ref(path):return dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
def rowmap(rows):return {(r['program'],r['id']):r for r in rows}
def variant_task(item,ident,phase,scenario='zero',owner='CONTROL',event='',expected=None):
 mode='single' if ident.startswith('S_') or ident=='JOURNAL_SINGLE_L1' else 'pipeline'
 rep='direct' if '_DIR_' in ident or ident.startswith('JOURNAL') else 'recurrent';L=2 if ident.endswith('L2') else 1;extra=[]
 if ident=='NATIVE':mode='native'
 if ident.startswith('JOURNAL'):extra=['--journal-service','--journal-merge-undo','--undo-batch-latency','2']
 if ident=='STRAT16_PIPE_L1':rep='stratum';extra=['--tap-budget','16']
 return make(item,ident,phase,scenario,owner,event,mode,rep,L,extra,expected)
def old_tasks(phase):
 path=V6/'configs'/(phase+'.lock.json');return load(path)['tasks'],ref(path)
def old_rows(phase):
 path=V6/'reports'/(phase+'.json')
 if phase=='EVALUATION_FAULT' and (V6/'reports/EVALUATION_FAULT_COMPLETE.json').exists():path=V6/'reports/EVALUATION_FAULT_COMPLETE.json'
 d=load(path);assert d['status'] in ['PASS','COMPLETED_WITH_FAILED_RUNS'];return d['tasks'],ref(path)
def inputs(phase):
 tasks,_=old_tasks(phase);items={t['program']:t['input'] for t in tasks}
 return [items[n] for n in ['qsort_small','dijkstra_small','sha1']]
def base_sites():return [json.loads(s) for s in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
def semantic_map(manifest):
 sites={'base:'+str(s['site_id']):s['site_id'] for s in base_sites() if not(manifest['direct'] and s['field']=='folded')}
 for s in manifest['additional_sites']:
  key='extra:'+':'.join(str(s[k]) for k in ['structure','word','bit','replica']);assert key not in sites;sites[key]=s['id']
 assert len(sites)==len(set(sites.values()))==manifest['total_bits'];return sites
def maps_for(rows,identifiers=POLICIES):
 return {i:semantic_map(load(ROOT/next(r for r in rows if r['id']==i)['output']/'logical_manifest.json')) for i in identifiers}
def remap_tape(task,new_rows):
 old_clean,_=old_rows('EVALUATION_CLEAN' if task['phase']=='EVALUATION_FAULT' else 'CLEAN_SCREEN')
 old=next(r for r in old_clean if r['program']==task['program'] and r['id']==task['id'])
 new=next(r for r in new_rows if r['program']==task['program'] and r['id']==task['id'])
 before={site:key for key,site in semantic_map(load(ROOT/old['output']/'logical_manifest.json')).items()}
 after=semantic_map(load(ROOT/new['output']/'logical_manifest.json'));lines=[];mapping={}
 for line in task.get('events_text','').splitlines():
  tick,ids=line.split();old_ids=list(map(int,ids.split(';')));new_ids=[]
  for old_id in old_ids:
   key=before[old_id];assert key in after,('NO_SEMANTIC_REPLICATION_TARGET',key)
   new_id=after[key];new_ids.append(new_id);mapping[str(old_id)]=dict(semantic_site=key,new_site_id=new_id)
  assert len(set(new_ids))==len(new_ids),'SEMANTIC_REMAP_COLLAPSED_EVENT'
  lines.append(tick+' '+';'.join(map(str,new_ids))+'\n')
 text=''.join(lines)
 if task['scenario']=='SOURCE':assert text==task['events_text'],'SOURCE_TAPE_MUST_BE_BYTE_IDENTICAL'
 return text,dict(numeric_tape_identical=text==task.get('events_text',''),mapping=mapping,
  old_schedule_sha256=hashlib.sha256(task.get('events_text','').encode()).hexdigest(),new_schedule_sha256=hashlib.sha256(text.encode()).hexdigest())
def frozen_candidate():
 path=OUT/'configs/CANDIDATE_FROZEN.lock.json';d=load(path)
 assert sha(OUT/'configs/PRODUCER.lock.json')==d['producer_sha256'],'STALE_FROZEN_CANDIDATE'
 assert d['primary_L']==d['II']==1 and d['holdout_master_base']==6215480000
 return d
def run_replay(phase,selected):
 d=frozen_candidate();cleans=load(OUT/'reports/EVALUATION_CLEAN.json')['tasks'];cm=rowmap(cleans);jobs=[];witness=[]
 for index,(task,repeat) in enumerate(selected):
  text,mapping=remap_tape(task,cleans);owner=task['owner'] if phase=='V6_REPLICATION' else f"OLD_FAILURE.{repeat}.{task['owner']}"
  t=variant_task(task['input'],task['id'],phase,task['scenario'],owner,text,cm[task['program'],task['id']]['instructions']);jobs.append(t)
  witness.append(dict(program=task['program'],scenario=task['scenario'],owner=owner,id=task['id'],original_owner=task['owner'],original_label=task['label'],repeat=repeat,mapping=mapping))
 write(OUT/'configs'/(phase+'_replication.lock.json'),dict(status='FIXED_BEFORE_REPLICATION_DISPATCH',candidate_sha256=sha(OUT/'configs/CANDIDATE_FROZEN.lock.json'),rows=witness,
  interpretation='Known-input/known-owner selected replay, not independent selection; no new ECC-site exposure claim from exact/semantic old tapes. Repeats are deterministic checks, not extra statistical owners.'))
 execute(jobs,phase,workers=8)
def make_holdout(items,cleans,master_base):
 cm=rowmap(cleans);maps=maps_for(cleans);union=sorted(set().union(*(set(v) for v in maps.values())));jobs=[];owners=[]
 raw=next(w['site_ids'] for w in load(ROOT/'sources/protection_scope.lock.json')['payload_words'] if len(w['site_ids'])==130)
 for wi,item in enumerate(items):
  name=item['name'];A=cm[name,'NATIVE']['cycles'];H=max(cm[name,i]['cycles'] for i in ['NATIVE']+POLICIES)
  for si,scenario in enumerate(['SOURCE','WHOLE']):
   for n in range(8):
    master=master_base+wi*1000000+si*10000+n;tt,ll,kk=rng(master,'time'),rng(master,'location'),rng(master,'K');cycle=0.;latent=[];events={i:[] for i in POLICIES}
    rate=1/A if scenario=='SOURCE' else (1.05e-14*20/3600*1e15)*len(union)/2e9
    while True:
     cycle+=float(tt.exponential(1/rate))
     if cycle>4*H:break
     tick=max(1,int(round(cycle*500)))
     if scenario=='SOURCE':
      K=1 if int(kk.integers(214))<205 else 2;start=int(ll.integers(130-K+1));sites=raw[start:start+K];latent.append(dict(tick=tick,K=K,sites=sites))
      for i in POLICIES:events[i].append(dict(tick=tick,sites=sites))
     else:
      key=union[int(ll.integers(len(union)))];latent.append(dict(tick=tick,site_key=key))
      for i in POLICIES:
       if key in maps[i]:events[i].append(dict(tick=tick,sites=[maps[i][key]]))
    owner=f'V7_OWNER_HOLDOUT.{si}.{n}'
    owners.append(dict(program=name,scenario=scenario,owner=owner,owner_index=n,master=master,time=descriptor(master,'time'),location=descriptor(master,'location'),K=descriptor(master,'K'),cap_cycles=4*H,clock_Hz=2000000000,cycle_ticks=500,lambda_union_or_target_per_cycle=rate,latent=latent,accepted=events,populations={i:len(v) for i,v in maps.items()} if scenario=='WHOLE' else {'raw_source':130}))
    for i in POLICIES:
     text=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events[i]);jobs.append(variant_task(item,i,'OWNER_HOLDOUT',scenario,owner,text,cm[name,i]['instructions']))
 return jobs,owners,maps

def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['declare','clean','pilot','freeze','evaluation_clean','replication','old_failure_replay','holdout'],required=True);a=p.parse_args()
 if a.phase=='declare':predeclare_round();return
 assert load(OUT/'configs/PRODUCER.lock.json')['status'].startswith('CPU_GATE_PASS'),'CORRECTED_PRODUCER_NOT_GATED'
 if a.phase=='clean':
  tasks,provenance=old_tasks('CLEAN_SCREEN');jobs=[variant_task(t['input'],t['id'],'CLEAN_SCREEN') for t in tasks]
  write(OUT/'configs/V6_CLEAN_REFERENCE.lock.json',dict(status='EXACT_OLD_INPUTS_AND_CONFIG_ROLES',source=provenance))
  rows=execute(jobs,'CLEAN_SCREEN',workers=8);cm=rowmap(rows);old,_=old_rows('CLEAN_SCREEN');om=rowmap(old)
  for item in inputs('CLEAN_SCREEN'):
   name=item['name']
   for k in ['cycles','instructions']:assert cm[name,'NATIVE'][k]==om[name,'NATIVE'][k],('NATIVE_PIN_CHANGED',name,k)
   for L in [1,2]:
    refrow=cm[name,f'P_REC_L{L}']
    for m in ['S','P']:
     for rep in ['REC','DIR']:
      row=cm[name,f'{m}_{rep}_L{L}']
      for k in ['cycles','instructions']:assert row[k]==refrow[k],('COMMON_MATCHED_EQUALITY',name,L,k)
      for k in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws','audit_identity_hash']:assert row['seu'][k]==refrow['seu'][k],('MATCHED_NORMAL_STATE',name,L,k)
   for k in ['cycles','instructions']:assert cm[name,'JOURNAL_SINGLE_L1'][k]==cm[name,'JOURNAL_PIPE_L1'][k],('JOURNAL_MATCHED_EQUALITY',name,k)
  write(OUT/'reports/CLEAN_ACCEPTANCE.json',dict(status='PASS',source=ref(OUT/'reports/CLEAN_SCREEN.json')))
 elif a.phase=='pilot':
  assert load(OUT/'reports/CLEAN_ACCEPTANCE.json')['status']=='PASS';tasks,source=old_tasks('PILOT');cleans=load(OUT/'reports/CLEAN_SCREEN.json')['tasks'];cm=rowmap(cleans);jobs=[];witness=[]
  for t in tasks:
   text,mapping=remap_tape(t,cleans);jobs.append(variant_task(t['input'],t['id'],'PILOT',t['scenario'],t['owner'],text,cm[t['program'],t['id']]['instructions']));witness.append(dict(original_label=t['label'],mapping=mapping))
  write(OUT/'configs/PILOT_replication.lock.json',dict(status='V6_SOURCE_PILOT_TAPES_BYTE_IDENTICAL',source=source,rows=witness));execute(jobs,'PILOT',workers=2)
 elif a.phase=='freeze':
  assert load(OUT/'reports/PILOT.json')['status']=='PASS';dest=OUT/'configs/CANDIDATE_FROZEN.lock.json';assert not dest.exists()
  tasks,source=old_tasks('EVALUATION_FAULT');old_owner=load(V6/'configs/EVALUATION_owners.lock.json')['owners'];hold_masters={6215480000+wi*1000000+si*10000+n for wi in range(3) for si in range(2) for n in range(8)}
  assert not hold_masters & {w['master'] for w in old_owner},'HOLDOUT_RNG_REUSE'
  write(dest,dict(status='V7_CANDIDATE_FIXED_BEFORE_REPLICATION_AND_OWNER_HOLDOUT',producer_sha256=sha(OUT/'configs/PRODUCER.lock.json'),round_sha256=sha(OUT/'configs/ROUND_PREDECLARED.lock.json'),primary_L=1,II=1,policies=POLICIES,inputs=inputs('EVALUATION_CLEAN'),replication_source=source,holdout_master_base=6215480000,holdout_owners_per_program_condition=8,conditions=['SOURCE','WHOLE'],interpretation='V6 replication is known data; new holdout has independent event owners on already seen inputs, not an input/workload holdout. WHOLE holdout exposes actual augmented ECC/control storage.'))
 elif a.phase=='evaluation_clean':
  d=frozen_candidate();execute([variant_task(item,i,'EVALUATION_CLEAN') for item in d['inputs'] for i in ['NATIVE']+POLICIES],'EVALUATION_CLEAN',workers=8)
 elif a.phase=='replication':
  tasks,_=old_tasks('EVALUATION_FAULT');run_replay('V6_REPLICATION',[(t,None) for t in tasks])
 elif a.phase=='old_failure_replay':
  tasks,_=old_tasks('EVALUATION_FAULT');rows,_=old_rows('EVALUATION_FAULT');failed={r['label'] for r in rows if r['status']!='PASS'};selected=[t for t in tasks if t['label'] in failed];assert len(selected)==3
  run_replay('OLD_FAILURE_REPLAY',[(t,repeat) for repeat in range(2) for t in selected])
 else:
  d=frozen_candidate();cleans=load(OUT/'reports/EVALUATION_CLEAN.json');assert cleans['status']=='PASS';jobs,owners,maps=make_holdout(d['inputs'],cleans['tasks'],d['holdout_master_base'])
  write(OUT/'configs/OWNER_HOLDOUT_maps.lock.json',dict(status='FROZEN_BEFORE_HOLDOUT_DISPATCH',maps=maps,producer_sha256=d['producer_sha256']))
  write(OUT/'configs/OWNER_HOLDOUT_owners.lock.json',dict(status='FROZEN_BEFORE_HOLDOUT_DISPATCH',owners=owners,candidate_sha256=sha(OUT/'configs/CANDIDATE_FROZEN.lock.json'),maps_sha256=sha(OUT/'configs/OWNER_HOLDOUT_maps.lock.json'),exposure='Actual v7 manifest including added protection/check storage; no target/mission calibration.'))
  execute(jobs,'OWNER_HOLDOUT',workers=8)
if __name__=='__main__':main()
