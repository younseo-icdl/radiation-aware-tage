"""Equal-resource clean/fault controls, not actual RTL timing claims."""
import csv,json,concurrent.futures
import v3_cpu_common as runner
from v3_cpu_common import *
runner.BINARY=ROOT/'third_party/gem5-costaware-v3-b/build/X86_STAGE0/gem5.opt';runner.CONFIG=ROOT/'gem5/o3_costaware_v3_B.py'
d=json.loads((OUT/'reports/CPU_DESIGN.json').read_text());clean={(r['program'],r['id']):r for r in d['tasks'] if r['scenario']=='zero' and r['status']=='PASS'}
inputs=json.loads((OUT/'configs/design_inputs.lock.json').read_text())['programs'];assert all((i['name'],'P0') in clean for i in inputs),'Finish actual clean development gate first'
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());fold=scope['payload_words'][18]['site_ids'][2]
variants=[dict(id='P0',scheme='P0',policy='LEGACY',k=0,C=0),dict(id='N1',scheme='P_ED',policy='N1',k=64,C=1),dict(id='V3_P',scheme='P_ED',policy='STAGED',k=64,C=1),dict(id='V3_D',scheme='P_ED',policy='H1',k=32,C=1,split=True),dict(id='H1_COMBINED',scheme='P_ED',policy='H1',k=32,C=1)]
jobs=[]
for i in inputs:
 A=clean[i['name'],'P0'];tick=A['cycles']*500//3
 for mode,L,II in [('SHARED2',2,1),('SHARED2',2,2),('SHARED1',1,1)]:
  for v in variants:
   for shape,event in [('zero',''),('fold_SBU',f'{tick} {fold}\n')]:
    jobs.append(dict(v,phase='B_RESOURCE',program=i['name'],input=i,U=0,owner=f"V3_RESOURCE_{i['name']}_{shape}",label=f"{i['name']}.{mode}.L{L}.II{II}.{shape}.{v['id']}",scenario=shape,resource=mode,L=L,II=II,events_text=event,expected_instructions=A['instructions'],max_ticks=A['cycles']*500*8,additional_args=['--resource-mode',mode,'--rmw-latency',str(L),'--rmw-ii',str(II)]+(['--decouple-shadow'] if v.get('split') else [])))
write(OUT/'configs/B_RESOURCE.runs.lock.json',dict(status='FROZEN_BEFORE_RUN',jobs=jobs,matched_source_detector_shadow=True,source_development_sha256=sha(OUT/'configs/design_inputs.lock.json'),role='sensitivity, one directed owner per input; no inferential workload population CI',SPLIT2_note='current SPLIT2 and SHARED2 both provision two service units; no independent arbitration benefit claimed'))
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for start in range(0,len(jobs),6):
  if used_cpu()>32*3600:raise SystemExit('Round checkpoint; fixed remaining rows retained')
  for r in pool.map(runner.run_cpu,jobs[start:start+6]):
   results.append(r);write(OUT/'reports/B_RESOURCE.json',dict(status='RUNNING',planned=len(jobs),completed=len(results),tasks=results));print(r['label'],r['status'],r.get('failure'),flush=True)
write(OUT/'reports/B_RESOURCE.json',dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED',planned=len(jobs),completed=len(results),tasks=results))
print('Actual resource sensitivity',len(results),'failed',sum(r['status']!='PASS' for r in results),flush=True)
