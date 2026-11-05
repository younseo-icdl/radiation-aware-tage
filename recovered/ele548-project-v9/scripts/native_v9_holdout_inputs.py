"""Prepare fresh inputs only after a measured development candidate is frozen."""
import argparse,hashlib,heapq,re,subprocess
from native_v9_common import *
from rng_namespace import rng,descriptor

def main():
 selection=OUT/'configs/CONFIRMATION_CANDIDATE.lock.json';assert selection.exists(),'Freeze actual candidate/domain before generating holdout inputs'
 dest=OUT/'configs/holdout_inputs.lock.json';assert not dest.exists(),'Immutable independent input declaration'
 old=load(OLD/'reports/E3_PUBLIC_WORKLOADS.json')['programs'];development={i['name']:i for i in load(OUT/'configs/development_inputs.lock.json')['programs']};items=[]
 for wi,original in enumerate(old):
  name=original['name'];master=9515480000+wi;lr=rng(master,'location');path=OUT/'inputs/holdout'/(name+'.dat');path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists()
  if name=='qsort_small':
   pool=(OLD/original['input']).read_text().split();chosen=lr.choice(len(pool),size=2000,replace=False);data='\n'.join(pool[int(i)] for i in chosen)+'\n'
  elif name=='dijkstra_small':
   matrix=[[9999]*100 for _ in range(100)]
   for a in range(100):
    matrix[a][a]=0;matrix[a][(a+1)%100]=int(lr.integers(1,80))
    for b in lr.choice(100,size=4,replace=False):
     if int(b)!=a:matrix[a][int(b)]=int(lr.integers(1,200))
   data='\n'.join(' '.join(map(str,row)) for row in matrix)+'\n'
  else:data=''.join(chr(32+int(x)) for x in lr.integers(0,95,size=131072))+'\n'
  path.write_text(data);item=dict(development[name]);binary=ROOT/item['binary'];assert sha(binary)==item['binary_sha256'];answer=path.with_suffix('.native.stdout')
  actual=subprocess.run([binary,path],capture_output=True,timeout=30);assert actual.returncode==0 and not actual.stderr;answer.write_bytes(actual.stdout);text=actual.stdout.decode('ascii')
  if name=='qsort_small':
   lines=text.strip().splitlines();assert lines[0]==f'Sorting {len(data.split())} elements.' and lines[1]=='' and lines[2:]==sorted(data.split(),reverse=True);validation='Independent Python full ordering and multiset'
  elif name=='sha1':assert ''.join(text.split())==hashlib.sha1(path.read_bytes()).hexdigest();validation='Independent Python hashlib digest'
  else:
   lines=text.strip().splitlines();assert len(lines)==20
   for a,line in enumerate(lines):
    match=re.fullmatch(r'Shortest path is (\d+) in cost\. Path is: (.*)',line);assert match;cost=int(match[1]);route=list(map(int,match[2].split()));target=(a+50)%100
    assert route[0]==a and route[-1]==target and sum(matrix[x][y] for x,y in zip(route,route[1:]))==cost
    distances=[float('inf')]*100;distances[a]=0;heap=[(0,a)]
    while heap:
     distance,node=heapq.heappop(heap)
     if distance!=distances[node]:continue
     for neighbor,weight in enumerate(matrix[node]):
      if weight!=9999 and distance+weight<distances[neighbor]:distances[neighbor]=distance+weight;heapq.heappush(heap,(distance+weight,neighbor))
    assert distances[target]==cost
   validation='Independent heap shortest distances plus printed route costs'
  assert sha(path)!=item['input_sha256'];item.update(input=str(path.relative_to(ROOT)),input_sha256=sha(path),input_bytes=path.stat().st_size,native_stdout=str(answer.relative_to(ROOT)),native_stdout_sha256=sha(answer),generation_rng=descriptor(master,'location'),independent_answer=validation,scope='Fresh input of same public program; generated after frozen candidate; no new-program or SPEC-score claim');items.append(item)
 write(dest,dict(status='NATIVE_VERIFIED_FRESH_INPUTS_AFTER_CANDIDATE_FREEZE',candidate=ref(selection),programs=items,input_master_base=9515480000))
 print('PASS fresh3native answers independently verified; no gem5 trial executed')
if __name__=='__main__':main()
