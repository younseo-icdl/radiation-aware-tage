"""Finish only the unstarted frozen suffix; retain the failed original report."""
from pipeline_v7_common import *
import hashlib


def ref(path):
 return dict(path=str(path.relative_to(ROOT)),sha256=sha(path))


prefix_path=OUT/'reports/EVALUATION_FAULT.json'
full_lock=OUT/'configs/EVALUATION_FAULT.lock.json'
continuation_lock=OUT/'configs/EVALUATION_FAULT_CONTINUATION.lock.json'
complete_path=OUT/'reports/EVALUATION_FAULT_COMPLETE.json'
assert not complete_path.exists(),'IMMUTABLE_COMPLETE_VIEW'
prefix=json.loads(prefix_path.read_text());frozen=json.loads(full_lock.read_text())
assert prefix['status']=='FAIL_RETAINED' and len(prefix['tasks'])==50 and prefix['planned']==96
assert len(frozen['tasks'])==96
for row,task in zip(prefix['tasks'],frozen['tasks']):
 for key,value in task.items():
  if key not in ('input','events_text'):assert row[key]==value,('PREFIX_TASK_CHANGED',key)
 assert row['schedule_sha256']==hashlib.sha256(task.get('events_text','').encode()).hexdigest()
failed=[r for r in prefix['tasks'] if r['status']!='PASS']
assert len(failed)==1 and failed[0]['label']=='dijkstra_small.SOURCE.PIPE_EVAL.0.6.P_REC_L1'
assert 'epoch wrap requires drained pipeline' in (ROOT/failed[0]['output']/'gem5.log').read_text()
remaining=frozen['tasks'][50:]
assert all(not (OUT/'reports/run_starts'/f"{t['phase']}.{t['label']}.json").exists() for t in remaining),'SUFFIX_ALREADY_STARTED'
declaration=dict(status='FROZEN_BEFORE_SUFFIX_DISPATCH',reason='BOUNDED_EPOCH_WRAP_MODEL_FAILURE_RETAINED',
 prefix_count=50,remainder_count=46,prefix_report=ref(prefix_path),frozen_full_task_lock=ref(full_lock),
 producer_lock=ref(OUT/'configs/PRODUCER.lock.json'),tasks=remaining,
 failed_log=ref(ROOT/failed[0]['output']/'gem5.log'),
 changes='Execution failure recognition only. No model/source/config/binary/input/seed/schedule/resource changes. No completed run repeated.')
assert not continuation_lock.exists(),'CONTINUATION_ALREADY_DECLARED'
write(continuation_lock,declaration)
suffix=execute(remaining,'EVALUATION_FAULT_REMAINDER',workers=8,
 allowed_failures=('FAIL_PIPELINE','pipeline queue control','inconsistent pipeline queue control',
 'FAIL_PROTOCOL invalid bounded history pointer','gem5 has encountered a segmentation fault',
 'epoch wrap requires drained pipeline'))
assert sha(prefix_path)==declaration['prefix_report']['sha256'] and sha(full_lock)==declaration['frozen_full_task_lock']['sha256']
assert sha(ROOT/declaration['failed_log']['path'])==declaration['failed_log']['sha256']
assert len(suffix)==46 and all(r['status']=='PASS' or r['status'].startswith('FAIL') for r in suffix)
continuation=dict(reason=declaration['reason'],prefix_count=50,remainder_count=46,
 prefix_report=ref(prefix_path),frozen_full_task_lock=ref(full_lock),
 remainder_report=ref(OUT/'reports/EVALUATION_FAULT_REMAINDER.json'),
 remainder_task_lock=ref(OUT/'configs/EVALUATION_FAULT_REMAINDER.lock.json'),
 producer_lock=ref(OUT/'configs/PRODUCER.lock.json'),continuation_lock=ref(continuation_lock))
write(complete_path,dict(status='COMPLETED_WITH_FAILED_RUNS',tasks=prefix['tasks']+suffix,planned=96,
 continuation=continuation,recorded_global_core_hours=global_cpu_seconds()/3600,new_core_hours=new_cpu_seconds()/3600))
print('COMPLETE96 frozen tasks; original50 retained; no failed cycles imputed; analyzer remains separate',flush=True)
