"""Bind/freeze source robustness schedules now; execute only after CPU design jobs finish."""
import json,csv
import numpy as np
from continuation_common import *
from rng_namespace import rng,descriptor
from parse_cern_clusters import parse
from run_cern_footprints import translations,tile_mappings
sel=json.loads((OUT/'configs/policy_selection.lock.json').read_text())['selection'];variants=[dict(id=s,scheme=s,policy='LEGACY',k=0) for s in ['P0','P_ED','P_ECC','P_TMR']]+[dict(id='N1',scheme='P_ED',policy='N1',k=int(sel['N1'].split('k')[-1])),dict(id='H1',scheme='P_ED',policy='H1',k=int(sel['H1'].split('k')[-1]))]
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());maps=tile_mappings(scope);payload=maps['word_contiguous'];out=OUT/'reports/model_robustness';out.mkdir(parents=True,exist_ok=True);models=[]
card=json.loads((ROOT/'data/curated/cern_footprint_model_card.json').read_text());catalog={}
for f in card['files']:
 p=ROOT/'data/raw/cern'/f['file'];assert sha(p)==f['raw_sha256'];rr=[r for r in parse(p.read_text()) if r['multiplicity_from_unique_coordinates']>=2]
 for r in rr:r['valid_translations']=translations(r['offsets_from_anchor']);assert r['valid_translations']
 catalog[f['file']]=rr
for f in catalog:
 for mapping in ['word_contiguous','word_interleaved']:models.append(dict(id=f'CERN_{f}_{mapping}',family='conditional_recorded_Kge2_CERN_footprint',file=f,mapping=mapping))
for duplicates in ['collapse','preserve']:
 for timing in ['observed','permuted','conditional_Poisson_fixedN']:models.append(dict(id=f'Flying_{duplicates}_{timing}',family='time_compressed_detection_SBU_sensitivity',duplicates=duplicates,timing=timing))
windows=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())['workloads'];jobs=[]
for wi,name in enumerate(['SHORT-INT-1','SHORT-FP-1']):
 file=next(w for w in windows if w['workload']==name)['split_files']['holdout'];assert sha(ROOT/file['path'])==file['sha256']
 for mi,model in enumerate(models):
  for n in range(2):
   master=2015480000+wi*1000000+mi*10000+n;tr=rng(master,'time');kr=rng(master,'catalog');lr=rng(master,'geometry');events=[];extra={}
   if model['family'].startswith('conditional'):
    t=0
    while True:
     t+=float(tr.exponential(1000))
     if t>=100000:break
     r=catalog[model['file']][int(kr.integers(len(catalog[model['file']])))];x,y=r['valid_translations'][int(lr.integers(len(r['valid_translations'])))];ids=[maps[model['mapping']][(y+dy)*16+x+dx] for dx,dy in r['offsets_from_anchor']];assert len(ids)==len(set(ids));events.append((t,ids))
    extra=dict(K_semantics='recorded coordinate-count catalog conditionalK>=2, not independent strikes',raw_source_sha256=sha(ROOT/'data/raw/cern'/model['file']),physical_target_layout_measured=False)
   else:
    source=ROOT/f'data/derived/flying_replay_{model["duplicates"]}.jsonl';rr=[json.loads(s) for s in source.read_text().splitlines()];times=np.array([r['time_seconds'] for r in rr]);span=times[-1]-times[0];gaps=np.diff(times)
    if model['timing']=='permuted':times=np.r_[0,np.cumsum(tr.permutation(gaps))]
    elif model['timing']=='conditional_Poisson_fixedN':times=np.sort(tr.uniform(0,span,size=len(rr)))
    else:times=times-times[0]
    for r,t in zip(rr,times):
     loc=rng(master,'location',int(r['source_group']),int(r['record_in_group']));events.append((float(t/span*99999),[payload[int(loc.integers(346))]]))
    extra=dict(source_rows=len(rr),source_span_seconds=float(span),record_source_sha256=sha(source),K_assumption='independent SBU per retained detection record; duplicates are not MCU',target_physical_rate_calibrated=False)
   schedule=out/f'{name}.{mi}.{n}.events';schedule.write_text(''.join(f'{t:.17g} '+ ';'.join(map(str,ids))+'\n' for t,ids in events))
   for v in variants:
    prefix=out/f'{name}.{mi}.{n}.{v["id"]}';cmd=[ROOT/'build/continuation_scheduled_final',ROOT/file['path'],'200000','100000',v['scheme'],schedule,model['id'],prefix,str(v['k']),v['policy']]
    jobs.append(dict(v,workload=name,scenario=model['id'],family=model['family'],trial=n,owner=f'CONT_SOURCE_HOLDOUT_V2_W{wi}_M{mi}_N{n}',master=master,command=list(map(str,cmd)),output=str(prefix.relative_to(ROOT)),input_sha256=file['sha256'],observed_window_relative_conditionals=[200000,300000],historical_input=True,event_schedule_sha256=sha(schedule),events=len(events),extra=extra))
write(OUT/'configs/source_robustness.lock.json',dict(status='FROZEN_BOUND_EXECUTABLE_SOURCE_PATTERNS',jobs=jobs,plans=len(jobs),max_workers=2,new_data_generalization=False,independence='fresh owners and different fault-observation window on historical traces;3fresh CPU inputs tested separately',models=models,scope_sha256=sha(ROOT/'sources/protection_scope.lock.json'),source_card_sha256=sha(ROOT/'data/curated/cern_footprint_model_card.json'),source_method_addendum_sha256=sha(ROOT/'data/curated/cern_method_review_addendum_20261013.json'),RTLPPA_measured=False))
print('FROZEN',len(jobs),'real source-pattern C++ replay cases, not yet executed')
