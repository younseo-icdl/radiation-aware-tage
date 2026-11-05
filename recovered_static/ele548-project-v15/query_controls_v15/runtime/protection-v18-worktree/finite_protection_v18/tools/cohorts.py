"""Predeclare disjoint v2 owners; native-verify new inputs before holdout use."""
import sys,json,pathlib,hashlib,heapq,re,subprocess
sys.dont_write_bytecode=True
import common as m
r=m.r;B=m.BASE
sys.path.insert(0,str(m.V9/'scripts'));from rng_namespace import rng,descriptor
PROGRAMS=['qsort_small','dijkstra_small','sha1'];SCENARIOS=['SSTAR346_SINGLE_SBU','SOURCE_RAW130_CHARM_2000S','WHOLE_K1_REF_SCALE1000000000000000']
MASTERS={'DEV':30000000000,'EVAL':31000000000,'INPUT':32000000000}
def prepare():
 old=r.load(m.V15/'reports/CPU18_PROPOSAL.lock.json');dev=[]
 for name in PROGRAMS:
  t=next(x for x in old['tasks'] if x['program']==name);dev.append({k:t[k] for k in ('program','program_binary','input','expected_stdout')})
 prior=[];known=set();digests=set();refs=[]
 def extract(v):
  if isinstance(v,dict):
   for k,x in v.items():
    if k=='master' and isinstance(x,int):known.add(x)
    if k=='SeedSequence_entropy' and isinstance(x,list) and len(x)==7 and x[:2]==[0x42505345,2]:known.add(x[2]+(x[3]<<32))
    if k=='input_sha256' and isinstance(x,str):digests.add(x)
    if k=='input' and isinstance(x,dict) and 'sha256' in x:digests.add(x['sha256'])
    extract(x)
  elif isinstance(v,list):
   for x in v:extract(x)
 for root in (pathlib.Path('/home/youns/workspace/ele548-project'),m.V9,pathlib.Path('/home/youns/workspace/ele548-project-v10')):
  for p in root.glob('**/configs/*.json'):
   if any(n in p.name.lower() for n in ('owner','input','seed','candidate','registry','frozen')):
    value=r.load(p);extract(value);refs.append(r.ref(p))
 owners=[]
 for phase,count in (('DEV',2),('EVAL',8)):
  for wi,name in enumerate(PROGRAMS):
   for si,scenario in enumerate(SCENARIOS):
    for index in range(count):
     master=MASTERS[phase]+wi*1000000+si*10000+index;assert master not in known,('OWNER_COLLISION',master)
     owners.append({'cohort':phase,'program':name,'scenario':scenario,'owner':f'{phase}.{wi}.{si}.{index}','master':master,**{role:descriptor(master,role) for role in ('time','K','location')}})
 new=[x['master'] for x in owners]+[MASTERS['INPUT']+i for i in range(3)];assert len(new)==len(set(new)) and not set(new)&known
 record={'status':'FROZEN_BEFORE_NEW_INPUTS_OR_FAULT_SCHEDULES','owners':owners,'input_master':MASTERS['INPUT'],'prior_registry_files':refs,'prior_distinct_masters':sorted(known),'prior_input_hashes':sorted(digests),'development':dev,'RNG_reference':r.ref(m.V9/'scripts/rng_namespace.py'),'scenarios':SCENARIOS,'analysis':'Per program/scenario paired owners; A clean P0, B fault P0, C clean method, D fault method. B-D primary; bootstrap95% and exact sign with Holm over method comparisons within program/scenario. Keep failures/nulls, negative/zero/helpful effects. No policy selection on EVAL.'}
 lock=B/'reports/COHORT_PREREGISTRATION.lock.json'
 if lock.exists():
  previous=r.load(lock);assert previous['owners']==owners and previous['development']==dev
 else:r.put(lock,record)
 cat=r.load('/home/youns/workspace/ele548-project/reports/E3_PUBLIC_WORKLOADS.json')['programs'];evaluation=[]
 for wi,item in enumerate(dev):
  name=item['program'];lr=rng(MASTERS['INPUT']+wi,'location');d=B/'runtime/inputs/EVAL'/name;d.mkdir(parents=True,exist_ok=True);path=d/'control.dat'
  if name=='qsort_small':
   source=next(x for x in cat if x['name']==name);poolpath=pathlib.Path('/home/youns/workspace/ele548-project')/source['input'];pool=poolpath.read_text().split();chosen=lr.choice(len(pool),size=2000,replace=False);data='\n'.join(pool[int(i)] for i in chosen)+'\n'
  elif name=='dijkstra_small':
   matrix=[[9999]*100 for _ in range(100)]
   for a in range(100):
    matrix[a][a]=0;matrix[a][(a+1)%100]=int(lr.integers(1,80))
    for q in lr.choice(100,size=4,replace=False):
     if int(q)!=a:matrix[a][int(q)]=int(lr.integers(1,200))
   data='\n'.join(' '.join(map(str,row)) for row in matrix)+'\n'
  else:data=''.join(chr(32+int(x)) for x in lr.integers(0,95,size=131072))+'\n'
  if path.exists():assert path.read_text()==data
  else:path.write_text(data)
  assert r.sha(path) not in digests and r.sha(path)!=item['input']['sha256'],'INPUT_COLLISION'
  control=d/'launch.R1.dat'
  with control.open('x') as f:f.write('1 '+str(path)+'\n')
  run=m.invoke('native_input_EVAL_A2_'+name,[item['program_binary']['path'],control],30);answer=pathlib.Path(run['stdout']['path']);assert not pathlib.Path(run['stderr']['path']).read_bytes();text=answer.read_text()
  if name=='qsort_small':
   lines=text.strip().splitlines();assert lines[0]==f'Sorting {len(data.split())} elements.' and lines[1]=='' and lines[2:]==sorted(data.split(),reverse=True)
  elif name=='sha1':assert ''.join(text.split())==hashlib.sha1(path.read_bytes()).hexdigest()
  else:
   lines=text.strip().splitlines();assert len(lines)==20
   for a,line in enumerate(lines):
    match=re.fullmatch(r'Shortest path is (\d+) in cost\. Path is: (.*)',line);assert match;cost=int(match[1]);route=list(map(int,match[2].split()));target=(a+50)%100
    assert route[0]==a and route[-1]==target and sum(matrix[x][y] for x,y in zip(route,route[1:]))==cost
    distance=[float('inf')]*100;distance[a]=0;heap=[(0,a)]
    while heap:
     value,node=heapq.heappop(heap)
     if value!=distance[node]:continue
     for neighbor,weight in enumerate(matrix[node]):
      if weight!=9999 and value+weight<distance[neighbor]:distance[neighbor]=value+weight;heapq.heappush(heap,(distance[neighbor],neighbor))
    assert distance[target]==cost
  evaluation.append({'program':name,'program_binary':item['program_binary'],'input':r.ref(control),'payload':r.ref(path),'expected_stdout':r.ref(answer),'native':run,'input_rng':descriptor(MASTERS['INPUT']+wi,'location'),'independent_answer_verified':True})
 r.put(B/'reports/COHORT_INPUTS.lock.json',{'status':'PASS_FRESH_NATIVE_AND_INDEPENDENT_ANSWER_CHECKS_NO_GEM5','DEV':dev,'EVAL':evaluation,'preregistration':r.ref(B/'reports/COHORT_PREREGISTRATION.lock.json')});print('COHORTS_NATIVE_VERIFIED',len(refs),len(known),flush=True)
if __name__=='__main__':prepare()
