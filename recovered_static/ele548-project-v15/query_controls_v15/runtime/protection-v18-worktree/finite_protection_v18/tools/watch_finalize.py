"""Read-only watcher; finalize actual artifacts after the existing driver exits."""
import sys,pathlib,time,json,subprocess,os,datetime
sys.dont_write_bytecode=True
import common as m
r=m.r;B=m.BASE

def alive(pid,start):
 p=pathlib.Path('/proc')/str(pid)
 try:
  fields=(p/'stat').read_text().rsplit(')',1)[1].split();return fields[19]==start and fields[0]!='Z'
 except OSError:return False

def main():
 saved=r.load(B/'reports/ACTUAL_RUNNING_DRIVER.lock.json');assert len(saved['processes'])==1;driver=saved['processes'][0];pid=driver['pid'];start=driver['start_ticks'];r.put(B/'reports/FINALIZATION_WATCHER.lock.json',{'status':'STARTED_WATCHING_EXISTING_PROCESS_NO_INTERRUPTION','watcher_pid':os.getpid(),'driver_pid':pid,'driver_start_ticks':start,'at_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'script':r.ref(__file__),'will_start_no_CPU_trials':True})
 while alive(pid,start):time.sleep(5)
 # An abnormal parent termination must not lead to racing live children.
 while True:
  active=[p for p in (B/'runtime/run_starts').glob('*.json') if not(pathlib.Path(r.load(p)['output'])/'EXECUTION.json').exists()]
  if not active:break
  time.sleep(5)
 result=m.invoke('actual_terminal_audit_A1',[sys.executable,B/'tools/finalize_actual.py'],120,8)
 if (B/'reports/FINITE_MATRIX_COMPLETED.json').exists():m.invoke('native_break_even_A1',[sys.executable,B/'tools/native_break_even.py'],120,8)
 label='TERMINAL_A1';m.invoke('terminal_archive_A1',[sys.executable,B/'tools/package_evidence.py','--label',label],300,64)
 r.put(B/'reports/FINALIZATION_WATCHER_DONE.json',{'status':'TERMINAL_AUDIT_AND_HANDOFF_CREATED','terminal_audit':r.ref(B/'reports/ACTUAL_TERMINAL_AUDIT.json'),'archive_report':r.ref(B/'reports'/('PACKAGE_'+label+'.json')),'resources':r.snapshot()});print('TERMINAL_EVIDENCE_FINALIZED',flush=True)
if __name__=='__main__':main()
