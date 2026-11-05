"""V18 predeclared matrices; common latent v2 events, actual manifest thinning."""
import sys,pathlib,json,math
sys.dont_write_bytecode=True
import cpu_runner as c
r=c.r;B=c.B
sys.path.insert(0,str(c.m.V9/'scripts'));from rng_namespace import rng,descriptor
METHODS=list(c.config.METHODS);SCENARIOS=['SSTAR346_SINGLE_SBU','SOURCE_RAW130_CHARM_2000S','WHOLE_K1_REF_SCALE1000000000000000']
def load_inputs():return r.load(B/'reports/COHORT_INPUTS.lock.json')
def make(item,method,phase,early=True,L=1):
 label='.'.join((phase,item['program'],method));return {**item,'label':label,'phase':phase,'method':method,'early':early,'query_L':L,'timeout_seconds':3600,'output':str(B/'runtime/cpu_trials'/label),'expected_applied_events':0}
def clean_tasks(cohort,variant='CLEAN'):
 phase=cohort+'_'+variant;methods=('P0','EXACT_DIRECT') if variant=='L2' else METHODS
 return [make(item,method,phase,early=variant!='SERIAL',L=2 if variant=='L2' else 1) for item in load_inputs()[cohort] for method in methods]
def rows(phase):
 answer=[]
 for p in sorted((B/'runtime/cpu_trials').glob(phase+'.*/EXECUTION.json')):answer.append(r.load(p))
 return answer
def semantic_map(manifest):
 result={};direct=manifest['representation']=='direct' if 'representation' in manifest else manifest['total_logical_bits']<77000
 # Direct detection is from absent actual fold region, never total population.
 direct=not any(z['name']=='fold' for z in manifest['regions']);widths=manifest['word_widths']
 def words():return [f'w{w}:b{bit}' for w,n in enumerate(widths) if not direct or w>=21 for bit in range(n)]
 for region in manifest['regions']:
  name=region['name'];n=region['bits'];keys=None
  if name in ('protect_stage_payload','protect_authorized_source_payload') or name.startswith('protect_replica') or name.startswith('protect_stage_replica'):keys=[name+':'+x for x in words()]
  elif name in ('protect_sidecars','protect_stage_sidecars'):
   codec='SECDED' if manifest['scheme']=='P_ECC' else 'parity';keys=[]
   for w,width in enumerate(widths):
    if direct and w<21:continue
    check=1
    if codec=='SECDED':
     q=1
     while (1<<q)<width+q+1:q+=1
     check=q+1
    keys.extend(f'{name}:{codec}:w{w}:c{bit}' for bit in range(check))
  elif name.startswith('lookup_payload_'):
   keys=[f'{name}:raw:b{bit}' for bit in range(130)] if direct else [f'{name}:fold:b{bit}' for bit in range(200)]
   keys += [f'{name}:path:b{bit}' for bit in range(16)]
  elif name.startswith('update_payload_'):
   keys=[] if direct else [f'{name}:recurrent_data:b{bit}' for bit in range(n-1)]
   keys += [name+':suppressed']
  if keys is None:keys=[f'{name}:b{bit}' for bit in range(n)]
  assert len(keys)==n,('SEMANTIC_REGION_WIDTH',name,n,len(keys))
  for bit,key in enumerate(keys):assert key not in result;result[key]=region['start']+bit
 assert len(result)==len(set(result.values()))==manifest['total_logical_bits'] and set(result.values())==set(range(manifest['total_logical_bits']))
 return result
def clean_accept(cohort):
 rr=rows(cohort+'_CLEAN');assert len(rr)==18 and all(x['status'].startswith('PASS') for x in rr)
 for item in load_inputs()[cohort]:
  subset=[x for x in rr if x['program']==item['program']];base=next(x for x in subset if x['method']=='P0')
  for x in subset:
   for key in ('simInsts',):assert x[key]==base[key],('CLEAN_ARCH',key)
   for key in ('committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash'):assert x['program_exit_seu'][key]==base['program_exit_seu'][key],('CLEAN_ARCH_RNG',key)
 r.put(B/'reports'/(cohort+'_CLEAN_ACCEPTANCE.json'),{'status':'PASS_ALL6_PROGRAM_OUTPUT_AND_ARCHITECTURE_SAME_RESOURCE','runs':[r.ref(pathlib.Path(x['task']['output'])/'EXECUTION.json') for x in rr]})
 return rr
def fault_plan(cohort):
 clean=rows(cohort+'_CLEAN');assert len(clean)==18 and r.load(B/'reports'/(cohort+'_CLEAN_ACCEPTANCE.json'))['status'].startswith('PASS');cm={(x['program'],x['method']):x for x in clean};items=load_inputs()[cohort]
 maps={method:semantic_map(r.load(cm[items[0]['program'],method]['manifest']['path'])) for method in METHODS}
 for item in items:
  for method in METHODS:assert maps[method]==semantic_map(r.load(cm[item['program'],method]['manifest']['path']))
 union=sorted(set().union(*(set(x) for x in maps.values())));preg=r.load(B/'reports/COHORT_PREREGISTRATION.lock.json');owners=[];tasks=[]
 for reg in [x for x in preg['owners'] if x['cohort']==cohort]:
  item=next(x for x in items if x['program']==reg['program']);program=item['program'];scenario=reg['scenario'];A=cm[program,'P0']['cycles'];H=max(cm[program,z]['cycles'] for z in METHODS);master=reg['master'];tt,ll,kk=rng(master,'time'),rng(master,'location'),rng(master,'K');methods=METHODS[:-1] if scenario==SCENARIOS[0] else METHODS;events={z:[] for z in methods};latent=[];rate=None
  if scenario==SCENARIOS[0]:
   tick=max(1,int(tt.integers(1,A*500+1)));site=int(ll.integers(346));widths=r.load(cm[program,'P0']['manifest']['path'])['word_widths'];w=0;bit=site
   while bit>=widths[w]:bit-=widths[w];w+=1
   latent=[{'tick':tick,'K':1,'word':w,'bit':bit}]
   for method in methods:events[method]=[(tick,[f'W{w}:{bit}'])]
  else:
   scale=scenario==SCENARIOS[2];rate=(1.05e-14*20/3600*10**15)*len(union)/2e9 if scale else 2000/2e9;cycle=0.
   while True:
    cycle+=float(tt.exponential(1/rate))
    if cycle>4*H:break
    tick=max(1,int(round(cycle*500)))
    if scale:
     key=union[int(ll.integers(len(union)))];latent.append({'tick':tick,'K':1,'site_key':key})
     for method in methods:
      if key in maps[method]:events[method].append((tick,[str(maps[method][key])]))
    else:
     K=1 if int(kk.integers(214))<205 else 2;age=int(ll.integers(131-K));latent.append({'tick':tick,'K':K,'raw_age':age})
     for method in methods:events[method].append((tick,[f'R{q}' for q in range(age,age+K)]))
  owners.append({**reg,'A':A,'H':H,'horizon_ticks':4*H*500,'lambda_per_cycle':rate,'union_population':len(union),'populations':{z:len(maps[z]) for z in methods},'latent':latent,'accepted_counts':{z:len(events[z]) for z in methods}})
  for method in methods:
   t=make(item,method,cohort+'_FAULT');t['label']='.'.join((cohort+'_FAULT',program,reg['owner'],scenario,method));t['output']=str(B/'runtime/cpu_trials'/t['label']);t['owner']=reg['owner'];t['scenario']=scenario;t['expected_applied_events']=None;t['tape_horizon_ticks']=4*H*500;t['architectural_reference']=r.ref(pathlib.Path(cm[program,method]['task']['output'])/'EXECUTION.json');p=B/'runtime/configs'/(t['label']+'.ticks')
   with p.open('x') as f:f.write(''.join(str(tick)+' '+';'.join(sites)+'\n' for tick,sites in events[method]))
   t['schedule']=r.ref(p);tasks.append(t)
 expected=102 if cohort=='DEV' else 408;assert len(tasks)==expected
 lock=B/'runtime/configs'/(cohort+'_FAULT_PLAN.lock.json');r.put(lock,{'status':'FROZEN_BEFORE_DISPATCH','tasks':tasks,'owners':owners,'semantic_union_size':len(union),'semantic_maps':maps,'cohorts':r.ref(B/'reports/COHORT_PREREGISTRATION.lock.json'),'clean_acceptance':r.ref(B/'reports'/(cohort+'_CLEAN_ACCEPTANCE.json'))});print(cohort,'FAULT_PLAN_FIXED',len(tasks),len(owners),len(union),flush=True);return tasks
