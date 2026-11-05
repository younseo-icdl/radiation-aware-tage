"""Frozen actual O3 development/evaluation runner; each row has real output evidence."""
import argparse,csv,json,statistics,concurrent.futures
import numpy as np
import v3_cpu_common as runner
from v3_cpu_common import *
from rng_namespace import rng,descriptor
from parse_cern_clusters import parse
from run_cern_footprints import translations,tile_mappings
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['design','evaluation'],required=True);p.add_argument('--workers',type=int,default=2);p.add_argument('--recover-finished-clean',action='store_true');a=p.parse_args();phase=a.phase
assert json.loads((OUT/'reports/B_CPU_GATE.json').read_text())['status']=='PASS'
runner.BINARY=ROOT/'third_party/gem5-costaware-v3-b/build/X86_STAGE0/gem5.opt';runner.CONFIG=ROOT/'gem5/o3_costaware_v3_B.py'
if phase=='evaluation':runner.select_final_endpoint()
inputs=json.loads((OUT/f'configs/{phase}_inputs.lock.json').read_text())['programs']
variants=[dict(id=s,scheme=s,policy='LEGACY',k=0,C=0 if s=='P0' else 1) for s in ['P0','P_ED','P_ECC','P_TMR']]+[dict(id='N1',scheme='P_ED',policy='N1',k=64,C=1),dict(id='V3_P',scheme='P_ED',policy='STAGED',k=64,C=1),dict(id='V3_D',scheme='P_ED',policy='H1',k=32,C=1,split=True)]
if phase=='evaluation':
 freeze=json.loads((OUT/'configs/CANDIDATE_SPEC.lock.json').read_text());assert freeze['status']=='FROZEN_BEFORE_NEW_EVALUATION'
 variants=freeze['variants']
else:variants += [dict(id='H1_COMBINED',scheme='P_ED',policy='H1',k=32,C=1)]
trials=5 if phase=='design' else 10;scenarios=['SBU_SINGLE','CHARM_6T','CERN_P29_INTERLEAVED']
base=2415480000 if phase=='design' else 2515480000
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());words=[w['site_ids'] for w in scope['payload_words']];sizes=np.array(list(map(len,words)));ends=np.cumsum(sizes)
geometry=tile_mappings(scope)['word_interleaved'];catalog=[r for r in parse((ROOT/'data/raw/cern/clust_p29MeV.txt').read_text()) if r['multiplicity_from_unique_coordinates']>=2]
for r in catalog:r['translations']=translations(r['offsets_from_anchor'])
results=[];jobs=[];clean={};report=OUT/f'reports/CPU_{phase.upper()}.json'
def persist(status):write(report,dict(status=status,phase=phase,planned=len(jobs),completed=len(results),tasks=results,binary_sha256=sha(runner.BINARY),host_core_hours=sum(r.get('host_cpu_seconds') or 0 for r in results)/3600))
for item in inputs:
 for v in variants:
  jobs.append(dict(v,phase='CPU_'+phase,program=item['name'],input=item,U=0,owner='V3_'+phase.upper()+'_ZERO_'+item['name'],label=item['name']+'.zero.'+v['id'],scenario='zero',trial=0,additional_args=['--resource-mode','SHARED2','--rmw-latency','1','--rmw-ii','1']+(['--decouple-shadow'] if v.get('split') else [])))
if a.recover_finished_clean:
 def finished_or_run(t):
  d=OUT/'reports'/t['phase']/t['label']
  if d.exists():
   assert (d/'seu.json').exists(),'Partial execution must be retained and diagnosed before recovery'
   return runner.recover_cpu(t)
  return runner.run_cpu(t)
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  for r in pool.map(finished_or_run,jobs):
   results.append(r);persist('RUNNING_CLEAN_RECOVERY');print('Actual clean',r['label'],r['status'],r.get('recovered_finished_artifact',False),flush=True)
   if r['status']=='PASS':clean[r['program'],r['id']]=r
 persist('RECOVERED_FINISHED_CLEAN')
else:
 persist('RUNNING_CLEAN')
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  for r in pool.map(runner.run_cpu,jobs):
   results.append(r);persist('RUNNING_CLEAN');print(r['label'],r['status'],r.get('failure'),flush=True)
   if r['status']=='PASS':clean[r['program'],r['id']]=r
if any(r['status']!='PASS' for r in results):persist('FAIL_CLEAN_RETAINED');raise SystemExit('No fault campaign after failed real clean gate')
extra=[]
for wi,item in enumerate(inputs):
 A=clean[item['name'],'P0']['cycles'];cap=4*A
 for si,scenario in enumerate(scenarios):
  for n in range(trials):
   master=base+wi*1000000+si*10000+n;tr=rng(master,'time');kr=rng(master,'K');lr=rng(master,'location');cr=rng(master,'catalog');gr=rng(master,'geometry');events=[]
   if scenario=='SBU_SINGLE':arrivals=[float(tr.uniform(.1*A,.8*A))]
   else:
    arrivals=[];t=0
    while True:
     t+=float(tr.exponential(1e6))
     if t>=cap:break
     arrivals.append(t)
   for t in arrivals:
    if scenario=='CERN_P29_INTERLEAVED':
     r=catalog[int(cr.integers(len(catalog)))];x,y=r['translations'][int(gr.integers(len(r['translations'])))];ids=[geometry[(y+dy)*16+x+dx] for dx,dy in r['offsets_from_anchor']]
    else:
     K=1 if scenario=='SBU_SINGLE' or int(kr.integers(214))<205 else 2
     word=words[int(np.searchsorted(ends,int(lr.integers(346)),side='right'))];start=int(lr.integers(len(word)-K+1));ids=word[start:start+K]
    events.append((max(1,int(round(t*500))),ids))
   text=''.join(str(t)+' '+ ';'.join(map(str,ids))+'\n' for t,ids in events)
   for v in variants:
    extra.append(dict(v,phase='CPU_'+phase,program=item['name'],input=item,U=0,owner=f'V3_{phase.upper()}_W{wi}_S{si}_N{n}',seed=master,namespaces={k:descriptor(master,k) for k in ['time','K','location','catalog','geometry']},label=f"{item['name']}.{scenario}.n{n}.{v['id']}",scenario=scenario,trial=n,events_text=text,max_ticks=cap*500,expected_instructions=clean[item['name'],'P0']['instructions'],additional_args=['--resource-mode','SHARED2','--rmw-latency','1','--rmw-ii','1']+(['--decouple-shadow'] if v.get('split') else [])))
jobs+=extra;write(OUT/f'configs/CPU_{phase}.runs.lock.json',dict(status='FROZEN_BEFORE_FAULT_OUTCOMES',jobs=jobs,variants=variants,scenarios=scenarios,trials_per_program_scenario=trials,conditional_rate_per_cycle=1e-6,rate_measured=False,baseline_endpoint_measured=True,cern_raw_sha256=sha(ROOT/'data/raw/cern/clust_p29MeV.txt'),scope_sha256=sha(ROOT/'sources/protection_scope.lock.json')))
forecast=statistics.mean(r['host_cpu_seconds'] for r in clean.values())*len(extra)*1.5/3600
write(OUT/f'reports/CPU_{phase}_FORECAST.json',dict(core_hours=forecast,charged_used=used_cpu()/3600,round_checkpoint=32))
if forecast+used_cpu()/3600>32:persist('ROUND_CHECKPOINT_BEFORE_DISPATCH');raise SystemExit('Fixed scope exceeds current round checkpoint; no sample reduction')
persist('RUNNING')
with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
 for start in range(0,len(extra),a.workers):
  if used_cpu()>=32*3600:persist('ROUND_CHECKPOINT_REACHED');raise SystemExit('Round checkpoint reached; preserve remaining plan')
  for r in pool.map(runner.run_cpu,extra[start:start+a.workers]):results.append(r);persist('RUNNING');print(r['label'],r['status'],r.get('failure'),flush=True)
persist('PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED')
print('actualCPU',phase,len(results),'valid',sum(r['status']=='PASS' for r in results),'failed',sum(r['status']!='PASS' for r in results),flush=True)
