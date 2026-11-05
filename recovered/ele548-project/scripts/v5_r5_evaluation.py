"""Frozen new inputs plus two unseen programs; no post-evaluation tuning."""
from v5_r5_common import *
from rng_namespace import rng,descriptor
import argparse
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['freeze','clean','fault'],required=True);p.add_argument('--version',type=int,choices=[1,2,3],default=1);a=p.parse_args()
prefix='EVALUATION' if a.version==1 else 'EVALUATION_V'+str(a.version)
policies=['NATIVE','PARITY64','BATCH_DIRECT','BATCH_STRAT16']
path=OUT/'configs'/(prefix+'_PREDECLARED.lock.json')
if a.phase=='freeze':
 assert not path.exists()
 inputs=json.loads((OLD/'configs/evaluation_inputs.lock.json').read_text())['programs']+json.loads((OLD/'configs/control_inputs.lock.json').read_text())['programs']
 if a.version>=2:
  compat=json.loads((OLD/('configs/basicmath_compat.lock.json' if a.version==2 else 'configs/basicmath_sseio.lock.json')).read_text());inputs=[x for x in inputs if x['name']!='basicmath_lp64']+[compat['program']]
 producer=json.loads((OUT/'configs/PRODUCER.lock.json').read_text())
 write(path,dict(status='FROZEN_BEFORE_ANY_EVALUATION_CPU',inputs=inputs,policies=policies,
   producer=producer,producer_lock_sha256=sha(OUT/'configs/PRODUCER.lock.json'),
   resource_lock_sha256=sha(OUT/'configs/variants.lock.json'),owners_per_program_condition=20,
   master_base={1:3415480000,2:3715480000,3:3815480000}[a.version],master_rule='base + program_index*1000000 + scenario_index*10000 + owner_index',
   conditions=['CHARM_RHO1_RAW130','WHOLE_SBU_SCALE1E15'],
   native_reference='NATIVE primary; PARITY64 reference; same previously frozen model and table algorithm.',
   criteria=dict(normal_overhead_percent=2,practical_net_gain_pp=.05,program_regression_warning_pp=.05,residual_mean_percent=2),
   inference='Paired owner resampling within program; 95% intervals; macro equal program weight. No winner from conditional data if failed full-population runs remain. No selection/tuning after this freeze.',
   safety='Known prototype pointer/queue failures retained separately, no imputed successful cycles; no fully qualified hardware candidate until total control-state behavior exists.',
   forbidden='New parameters, new candidate families, filtering helpful/zero faults, post-outcome owner selection',
   compatibility_revision='Only basicmath workload compatibility changed before fault evaluation; V3 also removes floating printf. Candidates/resources unchanged. Four compatible inputs reuse exact existing clean executions. Two concrete fixes maximum.' if a.version>=2 else None))
 print('Frozen 5 inputs,4 policies,2 conditions,20 owners:20 clean+800 fault CPU executions')
 raise SystemExit
lock=json.loads(path.read_text());assert lock['policies']==policies
assert sha(OUT/'configs/PRODUCER.lock.json')==lock['producer_lock_sha256']
inputs=lock['inputs'];jobs=[]
if a.phase=='clean':
 for item in inputs:
  if a.version>=2 and item['name']!=('basicmath_double' if a.version==2 else 'basicmath_sseio'):continue
  for ident in policies:jobs.append(make(item,ident,prefix+'_CLEAN','zero',prefix+'_FROZEN'))
 new=execute(jobs,prefix+'_CLEAN',workers=8,pilot_first_batch=2)
 if a.version>=2:
  source=OUT/'reports/EVALUATION_CLEAN.json';previous=json.loads(source.read_text())['tasks'];inherited=[r for r in previous if r['status']=='PASS']
  assert len(inherited)==16 and len(new)==4
  write(OUT/'reports'/(prefix+'_CLEAN_ALL.json'),dict(status='PASS',tasks=inherited+new,
    reused_actual_executions=16,new_actual_executions=4,inherited_report_sha256=sha(source),
    provenance='Merged view, not20newCPUexecutions. Original unsupported-ISA failures remain in original report.'))
else:
 cleans=json.loads((OUT/'reports'/('EVALUATION_CLEAN.json' if a.version==1 else prefix+'_CLEAN_ALL.json')).read_text())['tasks']
 def clean(name,ident):return next(r for r in cleans if r['program']==name and r['id']==ident)
 raw=next(w['site_ids'] for w in json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words'] if len(w['site_ids'])==130)
 base=[json.loads(s) for s in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
 maps={}
 for ident in policies:
  r=clean(inputs[0]['name'],ident);m=json.loads((ROOT/r['output']/'logical_manifest.json').read_text())
  entries={'base:'+str(s['site_id']):s['site_id'] for s in base if not(m['direct'] and s['field']=='folded')}
  for s in m['additional_sites']:entries['extra:'+':'.join(str(s[k]) for k in ['structure','word','bit','replica'])]=s['id']
  assert len(entries)==m['total_bits'];maps[ident]=entries
 universe=sorted(set().union(*(set(x) for x in maps.values())))
 owners=[]
 for wi,item in enumerate(inputs):
  H=max(clean(item['name'],ident)['cycles'] for ident in policies);A=clean(item['name'],'NATIVE')['cycles']
  for si,scenario in enumerate(lock['conditions']):
   for n in range(20):
    master=lock['master_base']+wi*1000000+si*10000+n;tt=rng(master,'time');ll=rng(master,'location');kk=rng(master,'K');cycle=0.;events={ident:[] for ident in policies};latent=[]
    rate=1/A if si==0 else (1.05e-14*20/3600*1e15)*len(universe)/2e9
    while True:
     cycle+=float(tt.exponential(1/rate))
     if cycle>4*H:break
     tick=max(1,int(round(cycle*500)))
     if si==0:
      K=1 if int(kk.integers(214))<205 else 2;start=int(ll.integers(130-K+1));sites=raw[start:start+K]
      latent.append(dict(tick=tick,K=K,sites=sites))
      for ident in policies:events[ident].append(dict(tick=tick,sites=sites))
     else:
      key=universe[int(ll.integers(len(universe)))];latent.append(dict(tick=tick,site_key=key))
      for ident in policies:
       if key in maps[ident]:events[ident].append(dict(tick=tick,sites=[maps[ident][key]]))
    owner=f'EVAL_V{a.version}.{si}.{n}'
    owners.append(dict(program=item['name'],owner=owner,scenario=scenario,master=master,
       time=descriptor(master,'time'),location=descriptor(master,'location'),K=descriptor(master,'K'),
       latent=latent,accepted=events,cap_cycles=4*H,lambda_union_or_target_cycle=rate,
       interpretation='Accelerated stress; not calibrated device/mission exposure. Future marks and zero-event realizations retained.'))
    for ident in policies:
     text=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events[ident])
     jobs.append(make(item,ident,prefix+'_FAULT',scenario,owner,text,expected=clean(item['name'],ident)['instructions']))
 write(OUT/'configs'/(prefix+'_owners.lock.json'),dict(status='FROZEN_BEFORE_FAULT_DISPATCH',owners=owners,union_sites=len(universe),populations={k:len(v) for k,v in maps.items()},predeclared_sha256=sha(path)))
 execute(jobs,prefix+'_FAULT',workers=8,allowed_fault_failures=(
  'FAIL_PROTOCOL invalid bounded history pointer','Pending response PC/type changed without cancellation',
  'gem5 has encountered a segmentation fault','queue SECDED DUE','illegal queue control encoding',
  'Prediction consumed before ready'))
 note('EVAL.FROZEN','IMPLEMENTED_CPU','Independent inputs/owners evaluated; no subsequent tuning',
      'Report paired performance, failed owners and all exposure limits per program','Final two-axis synthesis; no HDL')
