"""Same B1 schedule; deliberately short stop for state diagnosis, not performance."""
import sys,pathlib,os,fcntl,subprocess,time
sys.dont_write_bytecode=True
import cpu_runner as c
r=c.r;B=c.B
def main():
 method='P_ED_FREQUENT';label='DIAGNOSTIC_B1.'+method;producer=c.prepare_producer();d=B/'runtime/cpu_trials'/label
 # Wait until all original G2 cases end. No stop or setting change to them.
 while r.snapshot()['active']:time.sleep(1)
 with c.slot() as lease:
  with (B/'runtime/COUNT.lock').open('a+') as f:
   fcntl.flock(f,fcntl.LOCK_EX);r.snapshot(65,1);assert not d.exists();r.put(B/'runtime/run_starts'/(label+'.json'),{'label':label,'output':str(d),'phase':'REGRESSION_RESERVE_DIAGNOSTIC','reserved_cpu_seconds':65,'started':c.now()})
  d.mkdir();task=r.load(B/'runtime/cpu_trials/SBU_B1.P_ED_FREQUENT/EXECUTION.json')['task'];cpu=sorted(os.sched_getaffinity(0))[lease]
  command=[str(c.checked(producer['binary'])),'--outdir='+str(d),str(c.checked(producer['config'])),*c.config.args(method,task['program_binary']['path'],None,True,1,task['schedule']['path']),'--max-ticks','10000000','--execute'];env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib';start=time.perf_counter()
  with (d/'gem5.log').open('x') as log:proc=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(d/'gem5.time'),'/usr/bin/prlimit','--core=0','--','/usr/bin/taskset','-c',str(cpu),'/usr/bin/timeout','60',*command],stdout=log,stderr=subprocess.STDOUT,env=env)
  row={'status':'DIAGNOSTIC_NOT_PROGRAM_SUCCESS_NOT_PERFORMANCE','cycles':None,'command':command,'exit_code':proc.returncode,'host_cpu_seconds':r.seconds(d/'gem5.time'),'wall_seconds':time.perf_counter()-start,'intentionally_short_max_ticks':10000000}
  if (d/'seu.json').exists():row['snapshot']=r.load(d/'seu.json')
  r.put(d/'EXECUTION.json',row);r.put(B/'reports/RECOVERY_O3_DIAGNOSTIC_B1.json',row);print(row,flush=True)
if __name__=='__main__':main()
