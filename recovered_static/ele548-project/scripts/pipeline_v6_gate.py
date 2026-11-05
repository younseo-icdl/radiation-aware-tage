"""Small actual CPU gate before any pipeline performance screen."""
from pipeline_v6_common import *
import argparse,csv
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['base','fault','freeze'],required=True);a=p.parse_args()
item=dict(name='checksum',binary='build/checksum_freestanding',input='continuation_v3/runtime/inputs/checksum/ignored.dat',
 binary_sha256=sha(ROOT/'build/checksum_freestanding'),input_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/ignored.dat'),
 native_stdout_sha256=sha(ROOT/'continuation_v3/runtime/inputs/checksum/native.stdout'))
if a.phase=='base':
 assert json.loads((OUT/'reports/DIFFERENTIAL_GATE.json').read_text())['status']=='PASS_ACTUAL_TAGE_DIFFERENTIAL_AND_STAGE_SEU'
 for name in ['TRANSPORT_GATE.json','DIFFERENTIAL_GATE.json','INDEPENDENT_TAGE_GATE.json']:
  witness=json.loads((OUT/'reports'/name).read_text());assert witness['status'].startswith('PASS'),name
  for file,digest in witness.get('files_sha256',witness.get('hashes',{})).items():assert sha(ROOT/file)==digest,('STALE_CPP_GATE',name,file)
 from pipeline_v6_bind_build import bind_build
 bind_build()
 write(OUT/'configs/BUILT_PRODUCER.pending.json',dict(status='BUILT_NOT_CPU_GATED',binary=str(BINARY.relative_to(ROOT)),binary_sha256=sha(BINARY),
  config=str(CONFIG.relative_to(ROOT)),config_sha256=sha(CONFIG),source_lock_sha256=sha(OUT/'configs/source.lock.json'),build_binding_sha256=sha(OUT/'configs/BUILD_2_BINDING.json')))
 jobs=[make(item,'NATIVE','CPU_GATE_BASE',mode='native')]
 for L in [1,2]:
  for mode in ['single','pipeline']:
   for rep in ['recurrent','direct']:
    jobs.append(make(item,f'{mode}.{rep}.L{L}','CPU_GATE_BASE',mode=mode,rep=rep,L=L,extra=['--audit','--audit-limit','800']))
 for mode in ['single','pipeline']:
  jobs.append(make(item,'JOURNAL_'+mode,'CPU_GATE_BASE',mode=mode,rep='direct',L=1,
   extra=['--journal-service','--journal-merge-undo','--undo-batch-latency','2']))
 for scheme in ['P_ED','P_ECC','P_TMR']:
  t=make(item,scheme,'CPU_GATE_BASE',mode='native',extra=['--resource-mode','SHARED2']);t.update(scheme=scheme,C=1,policy='N1' if scheme!='P_TMR' else 'LEGACY',k=64 if scheme!='P_TMR' else 0);jobs.append(t)
 rows=execute(jobs,'CPU_GATE_BASE',workers=2)
 native=next(r for r in rows if r['id']=='NATIVE')
 old_native=next(r for r in json.loads((ROOT/'rate_state_v5/runtime_r5/reports/CPU_GATE.json').read_text())['tasks'] if r['id']=='NATIVE')
 for key in ['cycles','instructions']:assert native[key]==old_native[key],('NATIVE_COMPAT',key)
 for L in [1,2]:
  ref=next(r for r in rows if r['id']==f'single.recurrent.L{L}')
  for r in rows:
   if r['id'] not in [f'{m}.{rep}.L{L}' for m in ['single','pipeline'] for rep in ['recurrent','direct']]:continue
   for k in ['cycles','instructions']:assert r[k]==ref[k],('MATCHED_NOFAULT',L,r['id'],k)
   for k in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws','audit_identity_hash']:
    assert r['seu'][k]==ref['seu'][k],('MATCHED_STATE',L,r['id'],k)
 j1=next(r for r in rows if r['id']=='JOURNAL_single');j2=next(r for r in rows if r['id']=='JOURNAL_pipeline')
 for k in ['cycles','instructions']:assert j1[k]==j2[k],('JOURNAL_CAPACITY_EQUALITY',k)
 write(OUT/'reports/CPU_BASE_ACCEPTANCE.json',dict(status='PASS',same_L_single_pipeline_recurrent_direct_exact=True,native_R5_cycles_instructions_equal=True,report_sha256=sha(OUT/'reports/CPU_GATE_BASE.json')))
elif a.phase=='fault':
 assert json.loads((OUT/'reports/CPU_BASE_ACCEPTANCE.json').read_text())['status']=='PASS'
 base=json.loads((OUT/'reports/CPU_GATE_BASE.json').read_text())['tasks']
 direct=next(r for r in base if r['id']=='pipeline.direct.L1')
 trace=list(csv.DictReader((ROOT/direct['output']/'pipeline.csv').open()))
 first=next(r for r in trace if r['event']=='TABLE_PROVIDER_READ')
 manifest=json.loads((ROOT/direct['output']/'logical_manifest.json').read_text())
 origin=min(s['id'] for s in manifest['additional_sites'] if s['structure']=='pipeline_transport_control')
 raw=next(w['site_ids'] for w in json.loads((ROOT/'sources/protection_scope.lock.json').read_text())['payload_words'] if len(w['site_ids'])==130)
 jobs=[make(item,'RAW_'+rep,'CPU_GATE_FAULT','RAW_AFTER_ADDRESS','DIRECTED',str(int(first['tick'])-250)+' '+str(raw[0])+'\n',rep=rep) for rep in ['recurrent','direct']]
 # Slot0 response payload bit180 is the actual direction latch. Stage48
 # publishes before SEU49 and CPU50 consumes it in this directed test.
 response_direction=origin+46+4*(100+181)+100+180
 jobs.append(make(item,'RESPONSE_DIRECTION','CPU_GATE_FAULT','RESPONSE_SEU','DIRECTED',str(int(first['tick']))+' '+str(response_direction)+'\n',rep='direct'))
 # Invalid 3-bit queue count is a retained adverse execution failure.
 jobs.append(make(item,'QUEUE_CONTROL_INVALID','CPU_GATE_FAULT','METADATA_ADVERSE','DIRECTED',str(int(first['tick'])-250)+' '+str(origin+36)+'\n',rep='direct'))
 jobs.append(make(item,'REQUEST_EPOCH_INVALID','CPU_GATE_FAULT','METADATA_ADVERSE','DIRECTED',str(int(first['tick'])-250)+' '+str(origin+65)+'\n',rep='direct'))
 jobs.append(make(item,'RESPONSE_ID_INVALID','CPU_GATE_FAULT','METADATA_ADVERSE','DIRECTED',str(int(first['tick']))+' '+str(origin+1173)+'\n',rep='direct'))
 rows=execute(jobs,'CPU_GATE_FAULT',workers=2,allowed_failures=('pipeline queue control','inconsistent pipeline queue control','FAIL_PIPELINE'))
 assert all(r['status']=='PASS' for r in rows[:3])
 assert all(r['status']!='PASS' for r in rows[3:]),'Adverse metadata corruption silently counted as success'
 assert rows[2]['seu']['applied_events']==1
 write(OUT/'reports/CPU_FAULT_ACCEPTANCE.json',dict(status='PASS_WITH_RETAINED_ADVERSE_FAILURE',successful_fault_runs=3,adverse_failures=3,
  scope='Integrity tests do not qualify metadata safety. No failed cycles imputed.',report_sha256=sha(OUT/'reports/CPU_GATE_FAULT.json')))
else:
 assert json.loads((OUT/'reports/CPU_BASE_ACCEPTANCE.json').read_text())['status']=='PASS'
 assert json.loads((OUT/'reports/CPU_FAULT_ACCEPTANCE.json').read_text())['status']=='PASS_WITH_RETAINED_ADVERSE_FAILURE'
 d=json.loads((OUT/'configs/BUILT_PRODUCER.pending.json').read_text());assert sha(BINARY)==d['binary_sha256']
 d.update(status='CPU_GATE_PASS_WITH_UNSAFE_METADATA_ADVERSE_CASE_RETAINED',gate_sha256=sha(OUT/'reports/CPU_BASE_ACCEPTANCE.json'),fault_gate_sha256=sha(OUT/'reports/CPU_FAULT_ACCEPTANCE.json'))
 assert not (OUT/'configs/PRODUCER.lock.json').exists();write(OUT/'configs/PRODUCER.lock.json',d)
 print('Frozen pipeline producer; performance comparison allowed, metadata not hardware-qualified')
