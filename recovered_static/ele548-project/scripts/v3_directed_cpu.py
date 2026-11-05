"""Active-job/control and mid-repair CPU FI gates, with retained counterexamples."""
import csv, json, subprocess, concurrent.futures
import v3_cpu_common as runner
from v3_cpu_common import *

runner.BINARY=ROOT/'third_party/gem5-costaware-v3-b/build/X86_STAGE0/gem5.opt'
runner.CONFIG=ROOT/'gem5/o3_costaware_v3_B.py'
assert json.loads((OUT/'reports/B_CPU_GATE.json').read_text())['status']=='PASS'
gate=json.loads((OUT/'reports/B_CPU_GATE.json').read_text())
item=next(t['input'] for t in json.loads((OUT/'configs/CPU_design.runs.lock.json').read_text())['jobs']) if (OUT/'configs/CPU_design.runs.lock.json').exists() else None
# The native checksum gate owns the exact native reference, reconstructed read-only.
small=OUT/'inputs/checksum';binary=ROOT/'build/checksum_freestanding'
item=dict(name='checksum',binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),input=str((small/'ignored.dat').relative_to(ROOT)),input_sha256=sha(small/'ignored.dat'),native_stdout_sha256=sha(small/'native.stdout'))
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
raw=scope['payload_words'][21]['site_ids'][2];fold=scope['payload_words'][18]['site_ids'][2]
jobs=[]
for name,policy,k,split in [('P0','LEGACY',0,False),('P','STAGED',64,False),('Dshared2','H1',32,True)]:
 d=OUT/'reports/B_CPU_gate'/f'{name}.zero';m=json.loads((d/'logical_manifest.json').read_text())
 sites=m['additional_sites'];structures=sorted({s['structure'] for s in sites})
 records=list(csv.DictReader((d/'events.csv.resource.csv').open()))
 hot=next(int(r['tick']) for r in records if r['event']=='START' and r['domain']=='HOT_SOURCE')+250
 shadow=next((int(r['tick'])+250 for r in records if r['event']=='START' and r['domain']=='COMMIT_SHADOW'),hot)
 def append(label,events,expect='native_and_protocol'):
  jobs.append(dict(phase='B_DIRECTED',program='checksum',input=item,id=name,scheme='P0' if name=='P0' else 'P_ED',policy=policy,k=k,C=0 if name=='P0' else 1,U=0,owner='V3_DIRECTED_'+name+'_'+label,label=name+'.'+label,scenario=label,events_text=events,expected_behavior=expect,additional_args=['--resource-mode','SHARED2','--rmw-latency','1','--rmw-ii','1']+(['--decouple-shadow'] if split else [])))
 for structure in structures:
  ss=[s for s in sites if s['structure']==structure];target=ss[min(2,len(ss)-1)]['id']
  tick=shadow if structure.startswith('shadow_') or structure.startswith('actual_commit') else hot
  append('active_SBU.'+structure,f'{tick} {target}\n')
 # Two coded-control bits are detected, rather than silently reinterpreted.
 for structure in ['hot_queue_control','ready_credit_word','retire_reservation']:
  ss=[s for s in sites if s['structure']==structure]
  append('active_DUE.'+structure,f"{hot} {ss[0]['id']};{ss[1]['id']}\n",'explicit_domain_reset_or_retained_failure')
 if name=='Dshared2':
  rebuild=list(csv.DictReader((OUT/'reports/B_CPU_gate/Dshared2.fold/events.csv.rebuild.csv').open()))
  mid=int(rebuild[3]['tick'])+250
  for structure in ['committed_source','rebuild_accumulator','shadow_generation','actual_commit_sequence','shadow_completed_sequence']:
   ss=[s for s in sites if s['structure']==structure]
   append('mid_repair.'+structure,f"400000 {fold}\n{mid} {ss[2]['id']}\n",'restart_correction_or_retained_failure')
  append('mid_repair.source_DUE',f'400000 {fold}\n{mid} {raw};{raw+1}\n','source_loss_refill_or_retained_failure')
 if name=='P':
  ss=[s for s in sites if s['structure']=='staged_control']
  append('mid_refill.staged_SBU',f"400000 {fold}\n406250 {ss[2]['id']}\n")
 # Explicit code coverage limits; the model must keep native validation.
 append('fold_even_K2',f'400000 {fold};{fold+1}\n','parity_may_miss_not_total_coverage')
write(OUT/'configs/B_DIRECTED.runs.lock.json',dict(status='FROZEN_BEFORE_RUN',jobs=jobs,producer_sha256=sha(runner.BINARY),oracle=False,active_job_tick_rule='first START + half cycle; original clean sampled resource trace',mid_repair_tick_rule='fourth observed rebuild step + half cycle; directed qualification only'))
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(runner.run_cpu,jobs):
  results.append(r);write(OUT/'reports/B_DIRECTED.json',dict(status='RUNNING',planned=len(jobs),completed=len(results),tasks=results))
  print(r['label'],r['status'],r.get('failure'),flush=True)
write(OUT/'reports/B_DIRECTED.json',dict(status='PASS' if all(r['status']=='PASS' for r in results) else 'FAIL_RETAINED',planned=len(jobs),completed=len(results),tasks=results))
print('Directed CPU',len(results),'failures',sum(r['status']!='PASS' for r in results),flush=True)
