"""Native L0 CPU gates compare actual retired reads and training, not just totals."""
import argparse,csv
from native_v9_common import *

def bind():
 source=verify_sources();expected=load(OUT/'configs/BUILD_EXPECTED.json');assert expected['source_lock_sha256']==sha(OUT/'configs/source.lock.json')
 log=OUT/'reports'/('BUILD_'+str(expected['build_id'])+'.log');timing=log.with_suffix('.time')
 assert log.exists() and 'scons: done building targets.' in log.read_text(errors='replace'),'ACTUAL_BUILD_NOT_COMPLETE'
 assert seconds(timing)>0 and sha(BINARY)!=load(OUT/'configs/BOOTSTRAP.json')['copied_old_binary_sha256'],'COPIED_OLD_BINARY_IS_NOT_V9_BUILD'
 cpp_reports={}
 for name in ['TRANSPORT_GATE','DIFFERENTIAL_GATE','INDEPENDENT_TAGE_GATE','METADATA_SAFETY_GATE','SOURCE_HEAD_FIFO_GATE','READONLY_OBSERVATION_GATE','INJECTOR_ACCESS_GATE']:
  gate=load(OUT/'reports'/(name+'.json'));assert gate['status'].startswith('PASS'),name
  for file,digest in gate['hashes'].items():assert sha(ROOT/file)==digest,('STALE_CPP_GATE',name,file)
  cpp_reports[name]=ref(OUT/'reports'/(name+'.json'))
 binding=dict(status='ACTUAL_NEW_BUILD_BOUND_BEFORE_CPU',source=ref(OUT/'configs/source.lock.json'),expected=ref(OUT/'configs/BUILD_EXPECTED.json'),build_log=ref(log),build_time=ref(timing),binary_sha256=sha(BINARY),bootstrap=ref(OUT/'configs/BOOTSTRAP.json'),cpp_reports=cpp_reports)
 assert not (OUT/'configs/BUILD_BINDING.json').exists();write(OUT/'configs/BUILD_BINDING.json',binding)
 pending=dict(status='BUILT_V9_NOT_CPU_GATED',binary=str(BINARY.relative_to(ROOT)),binary_sha256=sha(BINARY),config=str(CONFIG.relative_to(ROOT)),config_sha256=sha(CONFIG),source_lock_sha256=sha(OUT/'configs/source.lock.json'),build_binding_sha256=sha(OUT/'configs/BUILD_BINDING.json'))
 write(OUT/'configs/BUILT_PRODUCER.pending.json',pending)
def table(row,file):
 with (ROOT/row['output']/file).open() as stream:return list(csv.DictReader(stream))
def compare_normal(rows):
 reference=next(r for r in rows if r['id']=='U');ref_reads=table(reference,'committed_audit.csv');ref_train=table(reference,'committed_audit.csv.training.csv');assert ref_reads and ref_train
 read_fields=['control_ordinal','op_ordinal','inst_ordinal','pc','micro_pc','identity_prefix','read_history','read_table','read_index','cond_pred','hit_bank','alt_bank','provider','rng_at_read','rng_draws_at_read']+[f'{part}_b{bank}' for part in ['index','tag'] for bank in range(1,8)]
 train_fields=['control_ordinal','op_ordinal','inst_ordinal','identity_prefix','pc','taken','nrand','rng_hash','history_before','history_after','rng_hash_before','rng_draws_before','rng_draws_after','table_before','table_after','training_calls_before','training_calls_after','allocations_before','allocations_after']
 for row in rows:
  for key in ['cycles','instructions']:assert row[key]==reference[key],('NATIVE_NORMAL_EXECUTION',row['id'],key)
  for key in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws','audit_identity_hash']:assert row['seu'][key]==reference['seu'][key],('NATIVE_NORMAL_STATE',row['id'],key)
  for filename,expected,fields in [('committed_audit.csv',ref_reads,read_fields),('committed_audit.csv.training.csv',ref_train,train_fields)]:
   actual=table(row,filename);assert len(actual)==len(expected),('NORMAL_AUDIT_LENGTH',row['id'],filename,len(actual),len(expected))
   for index,(a,b) in enumerate(zip(actual,expected)):
    for field in fields:assert field in a and a[field]==b[field],('NORMAL_AUDIT_FIRST_DIVERGENCE',row['id'],filename,index,a.get('control_ordinal'),a.get('pc'),field,a.get(field),b.get(field))
  assert int(ref_train[-1]['rng_draws_after'])==row['seu']['predictor_rng_draws'],'TRUNCATED_TRAINING_AUDIT'
 witness=dict(status='PASS_FULL_CHECKSUM_RETIRED_NATIVE_L0_SIX_FAMILIES',source=ref(OUT/'reports/GATE_NORMAL.json'),actual_runs=6,actual_retired_read_rows=len(ref_reads),actual_training_rows=len(ref_train),read_fields=read_fields,training_fields=train_fields,identity='retired control/op/instruction/PC/microPC/identity; speculative seq/request IDs excluded',scope='Full checksum audit under nofault. Same-stage check/vote is an assumption, not measured full-scheme physical feasibility.')
 write(OUT/'reports/GATE_NORMAL_ACCEPTANCE.json',witness)
def main():
 p=argparse.ArgumentParser();p.add_argument('--phase',choices=['bind','normal','sbu','due','freeze'],required=True);phase=p.parse_args().phase
 if phase=='bind':bind();return
 item=load(OUT/'configs/development_inputs.lock.json')['checksum']
 if phase=='normal':compare_normal(execute([make(item,i,'GATE_NORMAL',audit=True) for i in IDS],'GATE_NORMAL',workers=2));return
 if phase in ['sbu','due']:
  assert load(OUT/'reports/GATE_NORMAL_ACCEPTANCE.json')['status'].startswith('PASS');normal=load(OUT/'reports/GATE_NORMAL.json')['tasks'];manifest=ROOT/'sources/protection_scope.lock.json';raw=next(w['site_ids'] for w in load(manifest)['payload_words'] if len(w['site_ids'])==130)
  name='GATE_'+phase.upper();events='400000 '+';'.join(map(str,raw[:1 if phase=='sbu' else 2]))+'\n'
  result=execute([make(item,i,name,phase.upper(),'DIRECTED',events,expected=normal[0]['instructions']) for i in IDS],name,workers=2)
  for r in result:assert r['seu']['applied_events']==1 and r['seu']['applied_flips']==(1 if phase=='sbu' else 2)
  write(OUT/'reports'/(name+'_ACCEPTANCE.json'),dict(status='PASS_NATIVE_L0_DIRECTED_APPLICATION_AND_PROGRAM_OUTPUT',source=ref(OUT/'reports'/(name+'.json')),scope='Exact one/two physical flips and native answer checks. Even parity escapes and predictor-state mismatches remain actual outcomes, not architectural failure or zero damage.'))
  return
 for name in ['GATE_NORMAL','GATE_SBU','GATE_DUE']:assert load(OUT/'reports'/(name+'_ACCEPTANCE.json'))['status'].startswith('PASS')
 pending=load(OUT/'configs/BUILT_PRODUCER.pending.json');pending.update(status='PASS_NATIVE_L0_CPU_GATE_BEFORE_DEVELOPMENT',acceptance={name:sha(OUT/'reports'/(name+'_ACCEPTANCE.json')) for name in ['GATE_NORMAL','GATE_SBU','GATE_DUE']})
 assert not (OUT/'configs/PRODUCER.lock.json').exists();write(OUT/'configs/PRODUCER.lock.json',pending)
 note('L0.GATE','All six native families have equal nofault checksum retired reads/training; directed SBU/DUE keep program answers','Proceed with fixed development; no physical stage-fit claim','Clean18 then paired2scenario/2owner fault72')
if __name__=='__main__':main()
