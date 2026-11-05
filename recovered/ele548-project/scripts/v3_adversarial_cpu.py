"""Recorded codeword/replica limits; no relaxation of native program checks."""
import json,csv,concurrent.futures
import v3_cpu_common as runner
from v3_cpu_common import *
runner.BINARY=ROOT/'third_party/gem5-costaware-v3-b/build/X86_STAGE0/gem5.opt';runner.CONFIG=ROOT/'gem5/o3_costaware_v3_B.py'
binary=ROOT/'build/checksum_freestanding';p=OUT/'inputs/checksum'
item=dict(name='checksum',binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),input=str((p/'ignored.dat').relative_to(ROOT)),input_sha256=sha(p/'ignored.dat'),native_stdout_sha256=sha(p/'native.stdout'))
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());raw=scope['payload_words'][21]['site_ids'];fold=scope['payload_words'][18]['site_ids'];jobs=[]
for name,scheme,policy,k,split in [('Dshared2','P_ED','H1',32,True),('P','P_ED','STAGED',64,False),('TMR','P_TMR','LEGACY',0,False)]:
 m=json.loads((OUT/f'reports/B_CPU_gate/{name}.zero/logical_manifest.json').read_text());sites=m['additional_sites']
 def add(label,events,envelope):
  jobs.append(dict(id=name,phase='B_ADVERSARIAL',program='checksum',input=item,scheme=scheme,policy=policy,k=k,C=1,U=0,owner=f'V3_ADVERSARIAL_{name}_{label}',label=name+'.'+label,scenario=label,events_text=events,coding_envelope=envelope,additional_args=['--resource-mode','SHARED2','--rmw-latency','1','--rmw-ii','1']+(['--decouple-shadow'] if split else [])))
 if name=='Dshared2':
  ss=[s['id'] for s in sites if s['structure']=='committed_source' and s['word']==0]
  add('shadow_DUE_before_repair',f'400000 {ss[2]};{ss[3]}\n','two_errors_detectable_in_one_codeword')
  add('shadow_DUE_mid_repair',f'400000 {fold[2]}\n407750 {ss[2]};{ss[3]}\n','two_errors_detectable_in_one_codeword')
  add('spec_source_DUE',f'400000 {raw[2]};{raw[3]}\n','two_errors_detectable_in_one_codeword')
  add('spec_source_triple',f'400000 {raw[2]};{raw[3]};{raw[4]}\n','outside_SECDED_guarantee')
  ss=[s['id'] for s in sites if s['structure']=='hot_queue_slot' and s['word']==0]
  add('hot_descriptor_triple',f'73750 {ss[0]};{ss[1]};{ss[2]}\n','outside_SECDED_guarantee')
 if name=='P':
  ss=[s['id'] for s in sites if s['structure']=='staged_control']
  add('staged_DUE_mid_refill',f'400000 {fold[2]}\n406250 {ss[0]};{ss[1]}\n','two_errors_detectable_in_one_codeword')
  add('staged_triple_mid_refill',f'400000 {fold[2]}\n406250 {ss[0]};{ss[1]};{ss[2]}\n','outside_SECDED_guarantee')
 if name=='TMR':
  a=next(s['id'] for s in sites if s['structure']=='replica' and s['word']==18 and s['bit']==2 and s['replica']==1)
  b=next(s['id'] for s in sites if s['structure']=='replica' and s['word']==18 and s['bit']==2 and s['replica']==2)
  add('two_correlated_copies',f'400000 {a};{b}\n','outside_single_copy_TMR_guarantee')
write(OUT/'configs/B_ADVERSARIAL.lock.json',dict(status='FROZEN_BEFORE_RUN',jobs=jobs,notes='Outside-envelope cases are counterexamples, not guaranteed repairs. Every run still requires native correctness; retain execution/quality failures.'))
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(runner.run_cpu,jobs):rows.append(r);print(r['label'],r['status'],r.get('failure'),flush=True)
write(OUT/'reports/B_ADVERSARIAL.json',dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL_RETAINED',planned=len(jobs),completed=len(rows),tasks=rows,guaranteed_envelope_failures=sum(r['status']!='PASS' and r['coding_envelope']=='two_errors_detectable_in_one_codeword' for r in rows)))
