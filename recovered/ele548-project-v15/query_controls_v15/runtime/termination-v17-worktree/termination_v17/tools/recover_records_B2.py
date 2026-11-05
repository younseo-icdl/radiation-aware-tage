#!/usr/bin/env python3
"""Revalidate closed raw outputs after the B1 reporting exception; no CPU runs."""
from pathlib import Path
import datetime,json,re,sys
sys.dont_write_bytecode=True
import run as v
import resources_disk328 as r
B=v.BASE;OUT=r.scope['OUT'];m=v.m
def put(p,x):m.put(p,x)
def main():
 terminal=v.load(B/'runtime/remaining_B1/TERMINAL.json')
 assert terminal['observed_exit_code']==1 and terminal['session_id']==91126
 err=B/'runtime/remaining_B1/stderr';message=err.read_text()
 assert "AttributeError: module 'resources_disk328' has no attribute 'seconds'" in message
 assert not hasattr(r,'seconds') and callable(r.scope['seconds'])
 plan=v.load(B/'reports/REMAINING_B1.lock.json');tasks=plan['tasks'];assert len(tasks)==6
 for key in ('binary','config','observer','runner','guard'):v.original.checked(plan[key])
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:argv=(proc/'cmdline').read_bytes().split(b'\0')
  except OSError:continue
  assert not(argv and argv[0]==plan['binary']['path'].encode()),'CPU_CHILD_STILL_RUNNING'
 assert not (B/'reports/REMAINING_B1.json').exists()
 proof=[];rows=[]
 for t in tasks:
  d=Path(t['output']);assert d.exists() and not (d/'EXECUTION.json').exists()
  assert not (d/'validation_exception.txt').exists(),'ORIGINAL_VALIDATION_FAILED'
  text=(d/'gem5.time').read_text()
  # GNU time writes a diagnostic before these fields for a nonzero exit or
  # signal. The local zero/nonzero/signal probe is separately preserved.
  assert re.fullmatch(r'\d+(?:\.\d+)? \d+(?:\.\d+)? \d+\n',text),'NO_ZERO_EXIT_TIME_EVIDENCE'
  exit_evidence=v.load(B/'reports/TIME_EXIT_EVIDENCE_UNIT.json')
  assert exit_evidence['status']=='PASS_LOCAL_GNU_TIME_STATUS_CONVENTION' and exit_evidence['CPU_simulations']==0
  for key in ('program_binary','input','expected_stdout'):
   if t[key]:v.original.checked(t[key])
  result=v.validate(t,d,0)
  proof.append({'label':t['label'],'raw_files_before_record':{p.name:m.sha(p) for p in sorted(d.iterdir()) if p.is_file()},'validated_with':m.ref(B/'tools/run.py'),'program_exit_status_evidence':'GNU time exact numeric-only record under unchanged subprocess wrapper; nonzero/signal diagnostics rejected','validated':True})
  start=v.load(OUT/'run_starts'/(t['label']+'.json'))
  row={'label':t['label'],'program':t['program'],'representation':t['representation'],'source_L':t['source_L'],'status':'PASS_RAW_REVALIDATED_AFTER_DISPATCH_RECORD_FAILURE','cycles':None,'command':None,'planned_command_from_frozen_dispatcher':[plan['binary']['path'],'--outdir='+str(d),plan['config']['path'],*t['arguments']],'host_core':None,'wall_seconds':None,'missing_fields_reason':'B1 reporting exception before EXECUTION persistence; no reconstructed affinity or wall duration','started':start['started'],'ended':None,'recorded_at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'exit_code':0,'exit_code_evidence':proof[-1]['program_exit_status_evidence'],'host_cpu_seconds':r.scope['seconds'](d/'gem5.time'),'recording_recovery':m.ref(__file__)}
  row.update(result);row['hashes']=proof[-1]['raw_files_before_record'];rows.append((d,row))
 # Validate every case before adding any new record. Existing raw files and
 # the original failed dispatcher/config/guard remain byte-for-byte intact.
 put(B/'reports/RECORD_RECOVERY_B2.lock.json',{'status':'SIX_CLOSED_RAW_CASES_REVALIDATED_NO_SIMULATION_RERUN','runner':m.ref(__file__),'original_plan':m.ref(B/'reports/REMAINING_B1.lock.json'),'dispatcher_terminal':m.ref(B/'runtime/remaining_B1/TERMINAL.json'),'dispatcher_stderr':m.ref(err),'time_probe':m.ref(B/'reports/TIME_EXIT_EVIDENCE_UNIT.json'),'proof':proof})
 for d,row in rows:put(d/'EXECUTION.json',row)
 put(B/'reports/REMAINING_B2.json',{'status':'PASS_SIX_REMAINING_PROGRAMS_REVALIDATED_NO_RERUN','rows':[x[1] for x in rows],'record_recovery':m.ref(B/'reports/RECORD_RECOVERY_B2.lock.json'),'resources':r.snapshot(),'CPU_simulations_added_by_recovery':0,'retained_dispatch_failure':m.ref(err)})
 print('PASS_SIX_REMAINING_PROGRAMS_REVALIDATED_NO_RERUN',len(rows))
if __name__=='__main__':main()
