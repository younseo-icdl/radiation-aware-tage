import json,csv,concurrent.futures
from v3_common import *
from rng_namespace import rng,descriptor
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());words=[w['site_ids'] for w in scope['payload_words']];flat=sum(words,[])
windows=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())['workloads'];out=OUT/'reports/B_functional';out.mkdir(exist_ok=True);jobs=[]
variants=[dict(id='P0',scheme='P0',policy='LEGACY',k=0),dict(id='N1',scheme='P_ED',policy='N1',k=64),dict(id='V3_P',scheme='P_ED',policy='STAGED',k=64),dict(id='H1_FUNCTIONAL_REFERENCE',scheme='P_ED',policy='H1',k=32)]
for wi,name in enumerate(['SHORT-INT-1','SHORT-FP-1']):
 f=next(w for w in windows if w['workload']==name)['split_files']['design'];assert sha(ROOT/f['path'])==f['sha256']
 for si,shape in enumerate(['SBU','ATOMIC_K2']):
  for n in range(8):
   master=2325480000+wi*1000000+si*10000+n;g=rng(master,'location');K=si+1;word=words[int(g.integers(len(words)))];start=int(g.integers(len(word)-K+1));ids=word[start:start+K];file=out/f'{name}.{shape}.{n}.events';file.write_text('4096 '+ ';'.join(map(str,ids))+'\n')
   for v in variants:
    prefix=out/f'{name}.{shape}.{n}.{v["id"]}';cmd=[ROOT/'build/v3_B_scheduled',ROOT/f['path'],'500000','100000',v['scheme'],file,shape,prefix,str(v['k']),v['policy'],'INC','REBUILD']
    jobs.append(dict(v,owner=f'V3_DEV_B_W{wi}_S{si}_N{n}',seed=master,workload=name,scenario=shape,output=str(prefix.relative_to(ROOT)),command=list(map(str,cmd)),input_sha256=f['sha256'],schedule_sha256=sha(file),namespace=descriptor(master,'location')))
write(OUT/'configs/B_functional.lock.json',dict(status='FROZEN_BEFORE_EXECUTION',jobs=jobs,D_note='D source functional reference uses H1 no-lag behavior; actual asynchronous D tested in engine/gem5, not relabeled here',shapes='single SBU and atomic natural-codewordK2 stress; not physical eventrate'))
def run(t):
 r=timed(t['command'],ROOT/(t['output']+'.log'));r.update(t);r['status']='FAIL_EXECUTION'
 if r['exit_code']==0:
  file=ROOT/(t['output']+'.csv');m=list(csv.DictReader(file.open()));assert len(m)==1 and m[0]['status']=='PASS';r.update(status='PASS',metrics=m[0],CSV_sha256=sha(file))
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,jobs))
write(OUT/'reports/B_FUNCTIONAL.json',dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED',planned=len(jobs),completed=len(results),tasks=results,binary_sha256=sha(ROOT/'build/v3_B_scheduled')))
assert all(r['status']=='PASS' for r in results)
print('PASS',len(results),'actual fixed-stream policy comparisons; D no-lag reference separately labeled')
