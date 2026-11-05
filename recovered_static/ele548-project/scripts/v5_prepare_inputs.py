"""V5 fresh input generation; native checks reused with provenance from v3_prepare_inputs.py."""
import json,hashlib,subprocess,heapq,re
from v5_common import *
import argparse
p=argparse.ArgumentParser();p.add_argument("--phase",choices=["design","evaluation"],required=True);phase=p.parse_args().phase
base=3215480000 if phase=="design" else 3315480000
from rng_namespace import rng,descriptor
out=OUT/'inputs'/phase;out.mkdir(parents=True,exist_ok=True)
old=json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text());items=[]
for wi,item in enumerate(old['programs']):
 master=base+wi;lr=rng(master,'location');name=item['name'];path=out/(name+'.'+phase+'.dat')
 if name=='qsort_small':
  tokens=(ROOT/item['input']).read_text().split();indices=lr.choice(len(tokens),size=2000,replace=False);data='\n'.join(tokens[int(i)] for i in indices)+'\n'
 elif name=='dijkstra_small':
  matrix=[[9999]*100 for _ in range(100)]
  for i in range(100):
   matrix[i][i]=0;matrix[i][(i+1)%100]=int(lr.integers(1,80))
   for j in lr.choice(100,size=4,replace=False):
    if int(j)!=i:matrix[i][int(j)]=int(lr.integers(1,200))
  data='\n'.join(' '.join(map(str,row)) for row in matrix)+'\n'
 else:data=''.join(chr(32+int(x)) for x in lr.integers(0,95,size=131072))+'\n'
 if path.exists():assert path.read_text()==data
 else:path.write_text(data)
 stdout=out/(name+'.native.stdout');p=subprocess.run([ROOT/item['binary'],path],capture_output=True,timeout=30);assert p.returncode==0 and not p.stderr;stdout.write_bytes(p.stdout);text=p.stdout.decode('ascii')
 if name=='qsort_small':
  tokens=data.split();lines=text.strip().splitlines();assert lines[0]==f'Sorting {len(tokens)} elements.' and lines[1]=='' and lines[2:]==sorted(tokens,reverse=True);validation='Python full ordering/multiset'
 elif name=='sha1':assert ''.join(text.split())==hashlib.sha1(path.read_bytes()).hexdigest();validation='Python hashlib full digest'
 else:
  lines=text.strip().splitlines();assert len(lines)==20
  for a,line in enumerate(lines):
   match=re.fullmatch(r'Shortest path is (\d+) in cost\. Path is: (.*)',line);assert match
   cost=int(match[1]);route=list(map(int,match[2].split()));target=(a+50)%100;assert route[0]==a and route[-1]==target and sum(matrix[x][y] for x,y in zip(route,route[1:]))==cost
   distances=[float('inf')]*100;distances[a]=0;heap=[(0,a)]
   while heap:
    distance,node=heapq.heappop(heap)
    if distance!=distances[node]:continue
    for neighbor,weight in enumerate(matrix[node]):
     if weight!=9999 and distance+weight<distances[neighbor]:distances[neighbor]=distance+weight;heapq.heappush(heap,(distance+weight,neighbor))
   assert distances[target]==cost
  validation='Independent heap shortest distances; printed path endpoints/costs'
 assert sha(path)!=item['input_sha256']
 items.append(dict(name=name,binary=item['binary'],binary_sha256=item['binary_sha256'],input=str(path.relative_to(ROOT)),input_sha256=sha(path),input_bytes=path.stat().st_size,native_stdout=str(stdout.relative_to(ROOT)),native_stdout_sha256=sha(stdout),generation_rng=descriptor(master,'location'),independent_answer=validation,source_files=item['source_files']))
write(OUT/f'configs/{phase}_inputs.lock.json',dict(status='NATIVE_VERIFIED_FRESH_INPUTS_NOT_POLICY_EVALUATED',programs=items,phase=phase,input_generation_masters=[base+i for i in range(3)],generality='New inputs of same3publicMiBench programs, not new program/ISA or SPEC_CPU_score',workload_source_lock_sha256=sha(ROOT/'sources/public_workload_sources.lock.json')))
print('PASS fresh3inputs, native independent answers, same unmodified ELF binaries')
