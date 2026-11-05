"""Separate original native L0 reference; not common finite resource candidate."""
import sys,pathlib,os,fcntl,subprocess,time,concurrent.futures,re
sys.dont_write_bytecode=True
import cpu_runner as c,campaign as p
r=c.r;B=c.B

def freeze():
 path=B/'reports/NATIVE_REFERENCE_PRODUCER.lock.json'
 if path.exists():return r.load(path)
 planpath=pathlib.Path('/home/youns/workspace/ele548-project-v10/cost_v10/configs/NEXT_NATIVE_LIFETIME_BATCH.json');old=r.load(planpath);refs=old['source_references']
 binary=next(z for z in refs if z['path'].endswith('/gem5.opt'));cfg=next(z for z in refs if z['path'].endswith('/gem5/o3_native_v9r2.py'));src=next(z for z in refs if z['path'].endswith('/r2/runtime/configs/source.lock.json'))
 for x in (binary,cfg,src):c.checked(x)
 lock=r.load(src['path']);deps=[]
 for name,digest in lock['files'].items():z={'path':str(c.m.V9/name),'sha256':digest};c.checked(z);deps.append(z)
 for name,digest in lock['transport'].items():z={'path':str(c.m.V9/'third_party/gem5-native-v9r2/src'/name),'sha256':digest};c.checked(z);deps.append(z)
 destination=B/'runtime/producers/NATIVE_REFERENCE';destination.mkdir(parents=True,exist_ok=False);config=destination/'o3_native_v9r2.py';config.write_bytes(pathlib.Path(cfg['path']).read_bytes())
 value={'status':'FROZEN_PRIOR_NATIVE_L0_REFERENCE_NOT_FINITE_RESOURCE_COMPARISON','binary':binary,'config':r.ref(config),'source_lock':src,'source_dependencies':deps,'old_plan':r.ref(planpath)};r.put(path,value);return value

def one(task,producer,plan):
 with c.slot() as lease:
  out=pathlib.Path(task['output'])
  with (B/'runtime/COUNT.lock').open('a+') as f:
   fcntl.flock(f,fcntl.LOCK_EX);r.snapshot(3605,1);assert not out.exists()
   for key in ('program_binary','input','expected_stdout','payload'):
    if task.get(key):c.checked(task[key])
   binary=c.checked(producer['binary']);config=c.checked(producer['config']);r.put(B/'runtime/run_starts'/(task['label']+'.json'),{'label':task['label'],'output':str(out),'phase':'NATIVE_REFERENCE6','plan':r.ref(plan),'started':c.now(),'reserved_cpu_seconds':3605})
  out.mkdir();cpu=sorted(os.sched_getaffinity(0))[lease];args=['--binary',task['program_binary']['path'],'--input',task['input']['path'],'--scheme','P0','--pipeline-mode','native','--representation','recurrent','--lookup-latency','0','--lookup-ii','0','--max-ticks','2000000000000'];command=[str(binary),'--outdir='+str(out),str(config),*args];env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib';start=time.perf_counter();row={'status':'FAIL_RETAINED','cycles':None,'label':task['label'],'task':task,'command':command,'started':c.now()}
  try:
   with (out/'gem5.log').open('x') as log:proc=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(out/'gem5.time'),'/usr/bin/prlimit','--core=0','--fsize=524288','--','/usr/bin/taskset','-c',str(cpu),'/usr/bin/timeout','--signal=TERM','--kill-after=3','3600',*command],stdout=log,stderr=subprocess.STDOUT,env=env,cwd=B,timeout=3620)
   row['exit_code']=proc.returncode;assert proc.returncode==0 and r.sha(out/'program.stdout')==task['expected_stdout']['sha256'] and not(out/'program.stderr').read_bytes()
   assert not re.search(r'unimplemented syscall|ignoring syscall|instruction .*unimplemented',(out/'gem5.log').read_text(),re.I),'UNSUPPORTED_NOT_SUCCESS'
   s=r.load(out/'seu.json');assert s['pipeline_mode']=='native' and s['applied_events']==0 and s['pipeline_pending']==s['journal_pending']==s['native_pending_uncorrectable']==0
   st=c.stats(out/'stats.txt');row.update(status='PASS_NATIVE_REFERENCE_ONLY_NOT_SAME_FINITE_RESOURCE',cycles=int(st['system.cpu.numCycles']),IPC=float(st['system.cpu.ipc']),simInsts=int(st['simInsts']),seu=s)
  except Exception as exc:row['failure']=repr(exc)
  row.update(host_cpu_seconds=r.seconds(out/'gem5.time'),wall_seconds=time.perf_counter()-start,ended=c.now(),hashes={q.name:r.sha(q) for q in out.iterdir() if q.is_file()});r.put(out/'EXECUTION.json',row);return row

def run():
 producer=freeze();tasks=[]
 for cohort in ('DEV','EVAL'):
  for item in p.load_inputs()[cohort]:tasks.append({**item,'label':'.'.join(('NATIVE_REFERENCE',cohort,item['program'])),'output':str(B/'runtime/cpu_trials'/'.'.join(('NATIVE_REFERENCE',cohort,item['program'])))})
 plan=B/'runtime/configs/NATIVE_REFERENCE6.lock.json';r.put(plan,{'status':'FROZEN_BEFORE_DISPATCH','tasks':tasks,'producer':r.ref(B/'reports/NATIVE_REFERENCE_PRODUCER.lock.json'),'resources':r.snapshot(21630,6)})
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(lambda t:one(t,producer,plan),tasks))
 good=all(x['status'].startswith('PASS') for x in rows);r.put(B/'reports/NATIVE_REFERENCE6.json',{'status':'PASS' if good else 'FAIL_RETAINED','rows':rows,'resources':r.snapshot()})
 if not good:raise RuntimeError('NATIVE_REFERENCE_FAILURE_RETAINED')
 print('NATIVE_REFERENCE6_PASS',flush=True)
if __name__=='__main__':run()
