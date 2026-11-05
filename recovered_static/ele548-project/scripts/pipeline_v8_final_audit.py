"""Final V8 integrity/budget audit; no simulator, model changes or inferred safety."""
from pathlib import Path
import datetime,json,re,subprocess
from pipeline_v8_common import ROOT,OUT,PHASE_COUNTS,sha,write,verify_sources,all_rows,new_cpu_seconds,global_cpu_seconds,new_disk_gib,disk_gib,BINARY,CONFIG,FAILURE_RETENTION_POLICY,declared_failure_record
from pipeline_v8_analyze import load_phase
from pipeline_v6_final_audit import verify_success
RESULTS=ROOT/'rate_state_v5_pipeline_v8/results'
def require(ok,message):
 if not ok:raise RuntimeError('V8_FINAL_AUDIT: '+str(message))
def load(path):return json.loads(path.read_text())
def ref(path):return dict(path=str(path.relative_to(ROOT)),sha256=sha(path))
def verify_acceptance_bindings(producer):
 for field,name,phase,status in [
  ('gate_sha256','CPU_BASE_ACCEPTANCE','CPU_GATE_BASE','PASS_V8_NORMAL_AND_BASELINE_COMPATIBILITY'),
  ('fault_gate_sha256','CPU_FAULT_ACCEPTANCE','CPU_GATE_FAULT','PASS_V8_CORRECTED_METADATA_AND_LONG_WRAP')]:
  path=OUT/'reports'/(name+'.json');acceptance=load(path)
  require(producer.get(field)==sha(path),('STALE_PRODUCER_ACCEPTANCE_HASH',name))
  require(acceptance.get('status')==status and acceptance.get('source_sha256')==sha(OUT/'reports'/(phase+'.json')),('STALE_ACCEPTED_CPU_REPORT',phase))
  if phase=='CPU_GATE_FAULT':require(acceptance.get('successful_runs')==PHASE_COUNTS[phase] and acceptance.get('retained_failures')==0,'INCORRECT_FAULT_ACCEPTANCE_COUNTS')
 source_acceptance=load(OUT/'reports/CPU_SOURCE_ACCEPTANCE.json')
 require(producer.get('source_gate_sha256')==sha(OUT/'reports/CPU_SOURCE_ACCEPTANCE.json') and source_acceptance.get('source_sha256')==sha(OUT/'reports/CPU_GATE_SOURCE.json') and source_acceptance.get('clean_source_sha256')==sha(OUT/'reports/CPU_GATE_SOURCE_CLEAN.json') and source_acceptance.get('successful_runs')==PHASE_COUNTS['CPU_GATE_SOURCE_CLEAN']+PHASE_COUNTS['CPU_GATE_SOURCE'] and source_acceptance.get('status','').startswith('PASS'), 'STALE_SOURCE_GATE_ACCEPTANCE')
 require(producer.get('source_head_fifo_sha256')==sha(OUT/'reports/SOURCE_HEAD_FIFO_GATE.json'),'STALE_SOURCE_HEAD_FIFO_GATE')
 require(producer.get('metadata_safety_sha256')==sha(OUT/'reports/METADATA_SAFETY_GATE.json'),'STALE_METADATA_SAFETY_ACCEPTANCE')
 clean=load(OUT/'reports/CLEAN_ACCEPTANCE.json')
 require(clean.get('status')=='PASS' and clean.get('source')==ref(OUT/'reports/CLEAN_SCREEN.json'),'STALE_CLEAN_ACCEPTANCE')
def frozen_tasks_for_rows(rows,lock,lock_name):
 tasks=lock.get('tasks',[]);by_label={t['label']:t for t in tasks}
 require(len(by_label)==len(tasks),('DUPLICATE_FROZEN_LABEL',lock_name));result={}
 for row in rows:
  task=by_label.get(row['label']);require(task is not None,('UNLOCKED_EXECUTION',row['output'],lock_name))
  expected=str((OUT/'reports'/task['phase']/task['label']).relative_to(ROOT))
  require(row['output']==expected,('FROZEN_OUTPUT_CHANGED',row['output'],expected))
  require(row.get('producer_binary_sha256')==lock.get('binary_sha256') and row.get('config_sha256')==lock.get('config_sha256'),('EXECUTION_LOCK_PRODUCER_CHANGED',row['output']))
  for field,value in task.items():
   if field not in ['input','events_text']:require(row.get(field)==value,('FROZEN_TASK_CHANGED',row['output'],field))
  result[row['output']]=task
 return result
def verify_concurrency_amendment(rows,round_lock):
 path=OUT/'configs/CONCURRENCY_32_20261016.lock.json';d=load(path)
 require(round_lock.get('shared_slots')==8 and d.get('previous_shared_slots')==8 and d.get('shared_slots')==32,'CONCURRENCY_LIMIT_CHANGED')
 require(d.get('status')=='USER_AUTHORIZED_CONCURRENCY_ONLY_AMENDMENT' and d.get('round_sha256')==sha(OUT/'configs/ROUND_PREDECLARED.lock.json') and d.get('producer_sha256')==sha(OUT/'configs/PRODUCER.lock.json'),'UNBOUND_CONCURRENCY_AMENDMENT')
 at=datetime.datetime.fromisoformat(d['at']);require(at.tzinfo is not None,'NAIVE_AMENDMENT_TIMESTAMP')
 intervals=[]
 for row in rows:
  start=datetime.datetime.fromisoformat(row['started_at']);end=datetime.datetime.fromisoformat(row['ended_at'])
  require(start.tzinfo is not None and end.tzinfo is not None and start<end,('INVALID_TRIAL_INTERVAL',row['output']))
  intervals.append((start,end,row['phase'],row['output']))
 def measure(items,enforce=False):
  events=sorted([(a,1,name) for a,b,phase,name in items]+[(b,-1,name) for a,b,phase,name in items],key=lambda x:(x[0],x[1],x[2]))
  active=0;peak=0;before=0;after=0
  for tick,delta,name in events:
   active+=delta;require(active>=0,('INVALID_CONCURRENCY_SWEEP',name))
   peak=max(peak,active)
   if tick<at:before=max(before,active)
   else:after=max(after,active)
   if enforce:require(active<=(8 if tick<at else 32),('TRIAL_CONCURRENCY_BUDGET',tick.isoformat(),active))
  require(active==0,'UNTERMINATED_TRIAL_INTERVAL');return dict(peak=peak,before_amendment_peak=before,after_amendment_peak=after)
 actual=measure(intervals,True);by_phase={phase:measure([v for v in intervals if v[2]==phase])['peak'] for phase in sorted({v[2] for v in intervals})}
 last=[v for v in intervals if v[2]=='JOURNAL_HOLDOUT'];require(bool(last),'MISSING_LAST_PHASE_INTERVALS')
 start=min(v[0] for v in last);require(start<at and by_phase['JOURNAL_HOLDOUT']<=8,'ACTIVE_LAST_PHASE_WAS_NOT_PRESERVED_AT_EIGHT')
 return dict(amendment=ref(path),original_round=ref(OUT/'configs/ROUND_PREDECLARED.lock.json'),original_round_slots=8,authorized_future_slots=32,
  effective_existing_last_phase_slots=8,last_phase='JOURNAL_HOLDOUT',last_phase_first_trial_start=start.isoformat(),last_phase_started_before_amendment=True,
  actual_v8_trial_interval_concurrency=actual,actual_peak_by_phase=by_phase,actual_intervals=len(intervals),
  interpretation='Trial lease/start-to-end wall intervals, including runner overhead; not exact CPU-core utilization. Last phase was already running with its original eight-worker executor when32was authorized; no restart or claim that32were used.')

def main():
 round_lock=load(OUT/'configs/ROUND_PREDECLARED.lock.json');require(round_lock.get('failure_retention_policy')==FAILURE_RETENTION_POLICY,'FAILURE_RETENTION_POLICY_CHANGED')
 analysis_path=RESULTS/'ANALYSIS.lock.json';analysis=load(analysis_path)
 require(analysis['status']=='MEASURED_V8_SOFTWARE_REPLICATION_AND_OWNER_HOLDOUT' and analysis['actual_main_cpu']==sum(PHASE_COUNTS.values()),'FINAL_ANALYSIS_NOT_COMPLETE')
 for name,digest in analysis['outputs'].items():require(sha(RESULTS/name)==digest,('FINAL_OUTPUT_CHANGED',name))
 phases={};provenance=[];tasks_by_output={};phase_locks={}
 for name in PHASE_COUNTS:
  rows,p=load_phase(name);phases[name]=rows;provenance.append(p)
  lock=load(OUT/'configs'/(name+'.lock.json'));phase_locks[name]=lock
  frozen=frozen_tasks_for_rows(rows,lock,name)
  require(not tasks_by_output.keys() & frozen.keys(),('DUPLICATE_MAIN_EXECUTION',name));tasks_by_output.update(frozen)
 require(provenance==analysis['phases'],'FINAL_PHASE_PROVENANCE_CHANGED')
 require(all(r['status']=='PASS' for name in ['CPU_GATE_BASE','CPU_GATE_FAULT','CPU_GATE_SOURCE_CLEAN','CPU_GATE_SOURCE'] for r in phases[name]),'CORRECTED_CPU_GATES_FAILED')
 source=verify_sources();producer=load(OUT/'configs/PRODUCER.lock.json')
 require(producer['status']=='CPU_GATE_PASS_V8_LOSSLESS_SOURCE_FIFO_AND_TRANSPORT','STALE_PRODUCER_ACCEPTANCE')
 require(sha(BINARY)==producer['binary_sha256'] and sha(CONFIG)==producer['config_sha256'] and sha(OUT/'configs/source.lock.json')==producer['source_lock_sha256'],'PRODUCER_CHANGED')
 require(sha(OUT/'configs/BUILD_BINDING.json')==producer['build_binding_sha256'],'STALE_BUILD_BINDING')
 for name,lock in phase_locks.items():
  require(all(lock.get(k)==producer[k] for k in ['binary_sha256','config_sha256']),('PHASE_NOT_CURRENT_PRODUCER',name))
 verify_acceptance_bindings(producer)
 require('src/protection/word.hpp' in source['sources'],'UNLOCKED_METADATA_CODEC')
 require(source.get('private_backend')==['src/rate_state_v8','src/rate_state_v8_support'] and any(n.startswith('src/rate_state_v8/') for n in source['sources']) and any(n.startswith('src/rate_state_v8_support/') for n in source['sources']),'PRIVATE_BACKEND_NOT_LOCKED')
 require(subprocess.check_output(['git','-C',ROOT/'third_party/gem5-rate-pipeline-v8','rev-parse','HEAD'],text=True).strip()=='c8222cc67a399bfc01e8658dd14b30d5bfd634f9','GEM5_PIN_CHANGED')
 for name in ['TRANSPORT_GATE','DIFFERENTIAL_GATE','INDEPENDENT_TAGE_GATE','METADATA_SAFETY_GATE','SOURCE_HEAD_FIFO_GATE']:
  d=load(OUT/'reports'/(name+'.json'));require(d['status'].startswith('PASS'),('CPP_GATE_NOT_PASS',name));hashes=d.get('files_sha256',d.get('hashes',{})) or {a['path']:a['sha256'] for a in d.get('artifacts',[])}
  require(bool(hashes),('UNBOUND_CPP_GATE',name))
  for file,digest in hashes.items():require(sha(ROOT/file)==digest,('CPP_GATE_CHANGED',name,file))
 records=all_rows();own={k:r for k,r in records.items() if k.startswith('rate_state_v5_pipeline_v8/')};require(len(records)<=3200 and len(own)<=400,'CPU_BUDGET')
 concurrency=verify_concurrency_amendment(list(own.values()),round_lock)
 own_main={r['output']:r for rows in phases.values() for r in rows};require(len(own_main)==sum(PHASE_COUNTS.values()) and set(own_main)<=set(own),'DISTINCT_MAIN_CPU_COUNT')
 markers={p.name for p in (OUT/'reports/run_starts').glob('*.json')};record_markers={f"{r['phase']}.{r['label']}.json" for r in own.values()};require(markers==record_markers,'ORPHANED_OR_UNRECORDED_CPU_ATTEMPT')
 unsupported=[]
 for output,row in own.items():
  require(row['status']=='PASS' or str(row['status']).startswith('FAIL'),('NONTERMINAL_EXECUTION',output))
  if output not in tasks_by_output:
   # Retained corrective attempts bind to their own frozen task/producer,
   # never silently to a later candidate or a replacement event tape.
   lock_name=row['phase'];lock=load(OUT/'configs'/(lock_name+'.lock.json'))
   tasks_by_output.update(frozen_tasks_for_rows([row],lock,lock_name))
  path=ROOT/output;log=(path/'gem5.log').read_text(errors='replace')
  warnings=[line for line in log.splitlines() if re.search(r'instruction .*unimplemented|ignoring syscall|unimplemented syscall',line,re.I)]
  if warnings:unsupported.append(dict(output=output,status=row['status'],warnings=warnings));require(row['status']!='PASS',('UNSUPPORTED_ISA_MARKED_PASS',output))
  for name,digest in row.get('hashes',{}).items():require(sha(path/name)==digest,('RAW_ARTIFACT_CHANGED',output,name))
  if row['status']=='PASS':
   verify_success(row,tasks_by_output[output])
  else:
   require(row.get('cycles') is None,('FAILED_CYCLES_IMPUTED',output))
   retained=row.get('failure_retention')
   if retained:
    actual=declared_failure_record(row,log);require(actual is not None and retained==dict(**actual,raw_log_sha256=sha(path/'gem5.log')),('INVALID_DECLARED_FAILURE_RETENTION',output))
 require(global_cpu_seconds()<108*3600 and new_cpu_seconds()<12*3600,'CORE_HOUR_BUDGET')
 require(disk_gib()<34 and new_disk_gib()<8,'DISK_BUDGET')
 scope=dict(status='PASS_V8_EVIDENCE_INTEGRITY_NO_PHYSICAL_QUALIFICATION',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),analysis_lock_sha256=sha(analysis_path),phase_provenance=provenance,actual_distinct_global_cpu=len(records),actual_distinct_v8_cpu=len(own),actual_distinct_main_cpu=sum(PHASE_COUNTS.values()),actual_v8_failures=sum(r['status']!='PASS' for r in own.values()),global_recorded_core_h=global_cpu_seconds()/3600,v8_recorded_core_h=new_cpu_seconds()/3600,new_disk_gib=new_disk_gib(),combined_new_disk_gib=disk_gib(),limits=dict(new_cpu=400,global_cpu=3200,new_core_h=12,global_core_h=108,new_disk_gib=8,combined_disk_gib=34,original_shared_slots=8,authorized_future_shared_slots=32),concurrency=concurrency,unsupported_failed_runs=unsupported,preserved_old_files=len(load(OUT/'configs/PRESERVED_V7.lock.json')['hashes']),preservation=ref(OUT/'configs/PRESERVED_V7.lock.json'),fully_qualified_physical_candidates=0,scope='Integrity/software gate evidence only; no physical PPA/FIT or universal safety. Old v6 failures remain failures, no imputed cycles.')
 write(RESULTS/'EXECUTION_AUDIT.json',scope)
 software=dict(status='FINAL_V8_SOFTWARE_EVIDENCE',root=str(ROOT),branch=subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip(),source_commit_before_result_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),gem5_version='25.1.0.1',gem5_pin='c8222cc67a399bfc01e8658dd14b30d5bfd634f9',compiler='/opt/rh/gcc-toolset-11/enable',python=subprocess.check_output([ROOT/'.venv/bin/python','--version'],text=True).strip(),producer=producer,concurrency=concurrency,source=ref(OUT/'configs/source.lock.json'),metadata_codec=ref(ROOT/'src/protection/word.hpp'),reused_success_audit_helper=ref(ROOT/'scripts/pipeline_v6_final_audit.py'),build_binding=ref(OUT/'configs/BUILD_BINDING.json'),analysis=ref(analysis_path),execution_audit_sha256=sha(RESULTS/'EXECUTION_AUDIT.json'),no_eda_or_tcad=True)
 write(RESULTS/'software.lock.json',software);print('PASS V8 terminal raw/source/config/producer/old-preservation/budget integrity; no physical qualification')
if __name__=='__main__':main()
