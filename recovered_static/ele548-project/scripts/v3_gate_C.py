"""Corrected producer acceptance before freezing fresh evaluation."""
import json,csv,concurrent.futures
import v3_cpu_common as runner
from v3_cpu_common import *
runner.BINARY=ROOT/'third_party/gem5-costaware-v3-c/build/X86_STAGE0/gem5.opt';runner.CONFIG=ROOT/'gem5/o3_costaware_v3_C.py'
ready=json.loads((OUT/'reports/BUILD_C_READY.json').read_text());assert ready['status']=='COMPILED_C' and ready['binary_sha256']==sha(runner.BINARY) and ready['source_lock_sha256']==sha(OUT/'configs/source_C.lock.json')
binary=ROOT/'build/checksum_freestanding';p=OUT/'inputs/checksum'
item=dict(name='checksum',binary=str(binary.relative_to(ROOT)),binary_sha256=sha(binary),input=str((p/'ignored.dat').relative_to(ROOT)),input_sha256=sha(p/'ignored.dat'),native_stdout_sha256=sha(p/'native.stdout'))
old=json.loads((OUT/'reports/B_CPU_GATE.json').read_text())['tasks'];jobs=[]
def params_only(t):
 return {k:t[k] for k in ['id','scheme','policy','k','C','U','scenario','label','additional_args','expected_behavior','coding_envelope'] if k in t}
for t in old:
 if t['id'] not in ['P0','ED','ECC','TMR','N1','P','Dshared2','H1combined']:continue
 schedule=(ROOT/t['output']/'schedule.ticks').read_text()
 jobs.append(dict(params_only(t),input=item,phase='C_CPU_gate_v2',program='checksum',owner='V3_C_GATE_'+t['label'],events_text=schedule))
staged=json.loads((OUT/'reports/B_CPU_gate/P.zero/logical_manifest.json').read_text())['additional_sites'];ss=[s['id'] for s in staged if s['structure']=='staged_control']
template=next(t for t in jobs if t['label']=='P.zero')
jobs.append(dict(template,label='P.normal_metadata_DUE',scenario='normal_metadata_DUE',events_text=f'400000 {ss[0]};{ss[1]}\n',owner='V3_C_GATE_NORMAL_STAGE_DUE'))
for t in json.loads((OUT/'reports/B_DIRECTED.json').read_text())['tasks']:
 jobs.append(dict(params_only(t),input=item,phase='C_CPU_gate_v2',program='checksum',owner='V3_C_DIRECTED_'+t['label'],events_text=(ROOT/t['output']/'schedule.ticks').read_text()))
for inp in json.loads((OUT/'configs/design_inputs.lock.json').read_text())['programs']:
 jobs.append(dict(id='LEGACY_REFERENCE',input=inp,phase='C_CPU_gate_v2',program=inp['name'],scheme='P0',policy='LEGACY',k=0,C=0,U=0,scenario='zero',label=inp['name']+'.legacy_P0',owner='V3_C_LEGACY_REFERENCE_'+inp['name'],events_text='',additional_args=['--resource-mode','LEGACY']))
write(OUT/'configs/C_CPU_GATE.lock.json',dict(status='FROZEN_BEFORE_EXECUTION',jobs=jobs,source_lock_sha256=sha(OUT/'configs/source_C.lock.json'),binary_sha256=sha(runner.BINARY),normal_development_before_fix=True))
rows=[]
def checked_run(t):
 r=runner.run_cpu(t)
 if r['status']=='PASS' and t['scenario']=='zero' and t['id']!='LEGACY_REFERENCE':
  reference=next(x for x in old if x['label']==t['label'])
  assert r['cycles']==reference['cycles'] and r['seu']['canonical_base_state_hash']==reference['seu']['canonical_base_state_hash'] and r['seu']['predictor_rng_hash']==reference['seu']['predictor_rng_hash'],'Corrected producer changes normal execution'
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(checked_run,jobs):
  rows.append(r);write(OUT/'reports/C_CPU_GATE.json',dict(status='RUNNING',planned=len(jobs),completed=len(rows),tasks=rows));print(r['label'],r['status'],r.get('failure'),flush=True)
  if r['status']!='PASS':raise SystemExit('Corrected producer gate failed; no evaluation freeze')
write(OUT/'reports/C_CPU_GATE.json',dict(status='PASS',planned=len(jobs),completed=len(rows),tasks=rows,clean_bit_rng_cycle_equality=True,direct_refill_guard=True))
write(OUT/'configs/FINAL_PRODUCER.lock.json',dict(status='CPU_GATE_PASS_BEFORE_EVALUATION',binary=str(runner.BINARY.relative_to(ROOT)),binary_sha256=sha(runner.BINARY),config=str(runner.CONFIG.relative_to(ROOT)),config_sha256=sha(runner.CONFIG),source_lock='configs/source_C.lock.json',source_lock_sha256=sha(OUT/'configs/source_C.lock.json'),gate='reports/C_CPU_GATE.json',gate_sha256=sha(OUT/'reports/C_CPU_GATE.json'),normal_matches_prior_B=True,development_B_scope='source-informed conditional and equal-resource controls; whole B corrected by separate metadata gates',fix='Pre-retirement stage validation and fail-closed unexpected direct history mutation invariant; flush sampled resource ledger'))
print('Corrected producer PASS',len(rows),'native programs; zero results match B',flush=True)
