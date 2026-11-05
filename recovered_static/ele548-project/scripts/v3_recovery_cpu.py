import json,concurrent.futures
import v3_cpu_common as runner
from v3_cpu_common import *
from rng_namespace import rng,descriptor
runner.BINARY=ROOT/'build/gem5_v3_A.opt';runner.CONFIG=ROOT/'gem5/o3_costaware_v3_A.py'
inputs=json.loads((OUT/'configs/design_inputs.lock.json').read_text())['programs'][:2]
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());words=[w['site_ids'] for w in scope['payload_words']]
jobs=[]
for wi,item in enumerate(inputs):
 for w in [21,18]:
  for n in range(2):
   master=2335480000+wi*1000000+w*10000+n;g=rng(master,'location');site=words[w][int(g.integers(len(words[w])))];events='100000000 '+str(site)+'\n'
   for reset in [False,True]:
    name='RESET' if reset else 'REBUILD'
    jobs.append(dict(phase='A3_CPU',program=item['name'],input=item,scheme='P_ED',policy='H1',k=32,C=1,U=1,reset_recovery=reset,label=f'{item["name"]}.w{w}.n{n}.{name}',owner=f'V3_DEV_A3_CPU_W{wi}_B{w}_N{n}',scenario='single',trial=n,seed=master,namespace=descriptor(master,'location'),events_text=events,max_ticks=100000000000))
write(OUT/'configs/A3_CPU.lock.json',dict(status='FROZEN_BEFORE_CPU_RECOVERY_OUTCOMES',jobs=jobs,source_shadow_and_detector_matched=True,exploratory_two_owners_per_input_shape=True))
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(runner.run_cpu,jobs):results.append(r);write(OUT/'reports/A3_CPU.json',dict(status='RUNNING',planned=len(jobs),completed=len(results),tasks=results));print(r['label'],r['status'],flush=True)
write(OUT/'reports/A3_CPU.json',dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED',planned=len(jobs),completed=len(results),tasks=results))
print('Actual matched recovery CPU pilot complete',len(results))
