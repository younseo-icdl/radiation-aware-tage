"""Admission hold for this newly developed failed stage; no gem5 signals."""
import sys,os,pathlib,time,fcntl,signal,datetime
sys.dont_write_bytecode=True
import resources as r
B=r.BASE
with (B/'runtime/COUNT.lock').open('a+') as hold:
 fcntl.flock(hold,fcntl.LOCK_EX)
 state=r.snapshot();r.put(B/'reports/B2_CORRECTNESS_ADMISSION_HOLD.json',{'status':'NEW_DISPATCH_HELD_EXISTING_CPU_TRIALS_PRESERVED','at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'reason':'Actual rmw_primary_boundary_A1 failed: primary single-SEU after RMW physical write is re-encoded unchecked from physical source; parity/ECC/TMR detect0','failed_command':'common.invoke rmw_primary_boundary_A1_run','gate_run':r.ref(B/'runtime/rmw_primary_boundary_A1_run/EXECUTION.json'),'holder_pid':os.getpid(),'resources':state})
 while r.snapshot()['active']:time.sleep(1)
 # Only our new stage dispatcher remains. No active child CPU is terminated.
 saved=r.load(B/'reports/ACTUAL_RUNNING_DRIVER.lock.json')['processes'][0];pid=saved['pid'];p=pathlib.Path('/proc')/str(pid)
 if p.exists():
  fields=(p/'stat').read_text().rsplit(')',1)[1].split();assert fields[19]==saved['start_ticks'];assert 'run_round.py' in (p/'cmdline').read_bytes().decode(errors='replace');os.kill(pid,signal.SIGTERM)
  for _ in range(100):
   if not p.exists() or (p/'stat').read_text().rsplit(')',1)[1].split()[0]=='Z':break
   time.sleep(.1)
 r.put(B/'reports/B2_COORDINATOR_STOPPED_AFTER_CPU_COMPLETION.json',{'status':'FAILED_NEW_STAGE_COORDINATOR_ENDED_AFTER_ALL_ITS_CPU_RECORDS_CLOSED','no_gem5_process_signalled':True,'all_old_results_source_config_ELF_preserved':True,'resources':r.snapshot()});print('B2_NEW_STAGE_HELD_AND_COORDINATOR_ENDED_NO_CPU_INTERRUPTED',flush=True)
