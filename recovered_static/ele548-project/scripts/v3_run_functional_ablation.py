import csv,json,concurrent.futures
from v3_common import *
from rng_namespace import rng,descriptor
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());words=[r['site_ids'] for r in scope['payload_words']]
windows=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())['workloads']
variants=[dict(id='H1_RESET',scheme='P_ED',k=32,policy='H1',backend='INC',recovery='RESET'),dict(id='H1_REBUILD',scheme='P_ED',k=32,policy='H1',backend='INC',recovery='REBUILD')]
jobs=[];out=OUT/'reports/A3_functional_v2';out.mkdir(exist_ok=True)
for wi,name in enumerate(['SHORT-INT-1','SHORT-FP-1']):
 f=next(w for w in windows if w['workload']==name)['split_files']['design'];assert sha(ROOT/f['path'])==f['sha256']
 for shape,w in [('raw_SBU',21),('fold_SBU',0)]:
  for n in range(8):
   master=2315480000+wi*1000000+w*10000+n;g=rng(master,'location');word=w if shape=='raw_SBU' else 3*(n%7);id=words[word][int(g.integers(len(words[word])))];schedule=out/f'{name}.{shape}.n{n}.events';schedule.write_text('4096 '+str(id)+'\n')
   for v in variants:
    output=out/f'{name}.{shape}.n{n}.{v["id"]}';cmd=[ROOT/'build/v3_scheduled_matched',ROOT/f['path'],'500000','100000',v['scheme'],schedule,shape,output,str(v['k']),v['policy'],v['backend'],v['recovery']]
    jobs.append(dict(v,workload=name,shape=shape,owner=f'V3_DEV_A3_W{wi}_G{w}_N{n}',seed=master,namespace=descriptor(master,'location'),schedule_sha256=sha(schedule),input_sha256=f['sha256'],output=str(output.relative_to(ROOT)),command=list(map(str,cmd))))
write(OUT/'configs/A3_functional_v2.lock.json',dict(status='FROZEN_BEFORE_EXECUTION',jobs=jobs,k=32,controlled_source_shadow=True,old_input_development=True))
def run(t):
 r=timed(t['command'],ROOT/(t['output']+'.log'));r.update(t);r['status']='FAIL_EXECUTION'
 if r['exit_code']==0:
  f=ROOT/(t['output']+'.csv');row=list(csv.DictReader(f.open()));assert len(row)==1 and row[0]['status']=='PASS';r.update(status='PASS',metrics=row[0],CSV_sha256=sha(f))
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,jobs))
write(OUT/'reports/A3_FUNCTIONAL_V2.json',dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED',planned=len(jobs),completed=len(results),tasks=results,binary_sha256=sha(ROOT/'build/v3_scheduled_matched'),host_core_hours=sum(r['host_cpu_seconds'] or 0 for r in results)/3600))
assert all(r['status']=='PASS' for r in results)
print('PASS',len(results),'matched-source reset/rebuild trials')
