"""Bounded immutable trials, shared32 slots, terminal evidence before PASS."""
from pathlib import Path
from contextlib import contextmanager
from zoneinfo import ZoneInfo
import concurrent.futures,csv,datetime,fcntl,hashlib,json,os,re,subprocess,time,traceback
import common as m
import initialize as config
r=m.r;B=m.BASE
def now():return datetime.datetime.now(ZoneInfo('America/New_York')).isoformat()
@contextmanager
def slot():
 directory=Path('/home/youns/workspace/ele548-project/rate_state_v5/.cpu_slots');directory.mkdir(exist_ok=True)
 chosen=None
 while chosen is None:
  for i in range(32):
   file=(directory/(str(i)+'.lock')).open('a+')
   try:fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB);chosen=(i,file);break
   except BlockingIOError:file.close()
  if chosen is None:time.sleep(.1)
 try:yield chosen[0]
 finally:fcntl.flock(chosen[1],fcntl.LOCK_UN);chosen[1].close()
def stats(p):return {a.split()[0]:a.split()[1] for a in Path(p).read_text().splitlines() if a.strip() and not a.lstrip().startswith('#') and len(a.split())>=2}
def checked(x):
 p=Path(x['path']);assert r.sha(p)==x['sha256'],('CHANGED_REFERENCE',str(p));return p
def source_lock_checked(lock):
 for x in r.load(checked(lock))['files']:assert r.sha(x['path'])==x['sha256'],('LIVE_PRODUCER_SOURCE_CHANGED',x['path'])
def prepare_producer(name='A2'):
 record=B/'reports'/('PRODUCER_'+name+'.lock.json')
 if record.exists():return r.load(record)
 build_path=B/'reports'/('CPU_BUILD_'+name+'.json');build=r.load(build_path);checked(build['binary'])
 for dep in build['actual_dependencies']:checked(dep)
 destination=B/'runtime/producers'/name/'config';destination.mkdir(parents=True,exist_ok=False)
 for filename in ('o3_protection_v18.py','observer_v18.py'):
  old=B/'gem5_overlay'/filename;new=destination/filename;new.write_bytes(old.read_bytes())
 plan=r.load(build['plan']['path']);source_lock_checked(plan['source_lock'])
 value={'status':'FROZEN_BUILT_PRODUCER_BEFORE_CPU','build':r.ref(build_path),'binary':build['binary'],'config':r.ref(destination/'o3_protection_v18.py'),'observer':r.ref(destination/'observer_v18.py'),'source_lock':plan['source_lock'],'actual_dependencies':build['actual_dependencies'],'authorization':r.ref(r.AUTH),'execution_tools':[r.ref(B/'tools'/x) for x in ('cpu_runner.py','gate_cpu.py')],'at':now()}
 r.put(record,value);return value
def validate(task,d,exit_code):
 assert exit_code==0,('PROCESS_FAILURE',exit_code)
 assert r.sha(d/'program.stdout')==task['expected_stdout']['sha256'],'PROGRAM_ANSWER_MISMATCH'
 assert (d/'program.stderr').read_text()=='','PROGRAM_STDERR'
 s=r.load(d/'seu.program_exit.json');end=r.load(d/'seu.json');trace=r.load(d/'termination_trace.json');manifest=r.load(d/'logical_manifest.json');st=stats(d/'stats.txt')
 assert trace['status']=='PASS_ACTUAL_HELPER_COMPLETION_FROZEN_FAULT_CENSOR' and trace['source_cycles_observed']<=64
 assert s['conserved'] and end['conserved'] and end['early_pending']==end['lookup_pending']==end['source_pending']==0 and end['protection_pipeline_drained']
 assert end['ingress_enqueued']==end['ingress_issued'] and s['lookups']==s['lookup_consumed']+s['early_pending']
 for key in ('applied_events','applied_flips','censor_tick','scheduled_events','future_events_censored','committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash'):assert s[key]==end[key],('POST_EXIT_CHANGED_FIXED_VALUE',key)
 assert s['applied_events']+s['future_events_censored']==s['scheduled_events'] and s['censor_tick']==s['tick'] and s['faults_frozen']
 scheme,k,rep=config.METHODS[task['method']]
 assert manifest['scheme']==s['scheme']==scheme and manifest['inspection_interval']==s['inspection_interval']==k
 assert manifest['source_query_L']==task.get('query_L',1) and manifest['source_update_L']==1 and manifest['II']==1 and manifest['protection_check_L']==1
 at=0
 for region in manifest['regions']:assert region['start']==at and region['bits']>0;at+=region['bits']
 assert at==manifest['total_logical_bits'] and sum(manifest['word_widths'])==346
 events=list(csv.DictReader((d/'events.csv').open()));groups={}
 for item in events:
  assert item['before'] in ('0','1') and item['after'] in ('0','1') and item['before']!=item['after']
  assert int(item['tick'])<=s['tick'] and 0<=int(item['logical_id'])<at
  groups.setdefault(int(item['event']),[]).append(item)
 assert len(groups)==s['applied_events'] and len(events)==s['applied_flips'] and set(groups)==set(range(len(groups)))
 for items in groups.values():assert len({int(x['logical_id']) for x in items})==len(items) and len({x['tick'] for x in items})==1
 if task.get('expected_applied_events') is not None:assert s['applied_events']==task['expected_applied_events'],'EXPECTED_GATE_EVENTS_NOT_APPLIED'
 if task.get('gate_kind')=='MID_STAGE_DOUBLE':
  assert all(x['conditional_gate']=='1' and x['stage_phase']=='1' and x['stage_lookup']=='0' for x in events)
  ticks=[int(groups[n][0]['tick']) for n in sorted(groups)];assert ticks[1]==ticks[0]+1
  if task['method']=='P_ECC':assert s['protection_DUE']>0 and s['protection_resets']>0,'ACTUAL_ECC_DOUBLE_DUE_NOT_SEEN'
 if task.get('architectural_reference'):
  reference=r.load(checked(task['architectural_reference']));reference=reference.get('program_exit_seu',reference.get('seu'))
  for key in ('committed_ops','committed_controls','committed_identity','predictor_rng_draws','predictor_rng_hash'):assert s[key]==reference[key],('ARCHITECTURAL_OR_RNG_MISMATCH',key)
 if task.get('tape_horizon_ticks'):assert s['tick']<=task['tape_horizon_ticks'],'TAPE_HORIZON_EXCEEDED'
 cycles=int(st['system.cpu.numCycles']);ipc=float(st['system.cpu.ipc']);assert cycles>0 and ipc>0
 return {'cycles':cycles,'IPC':ipc,'simInsts':int(st['simInsts']),'program_exit_seu':s,'seu':end,'manifest':r.ref(d/'logical_manifest.json'),'post_exit_cycles':trace['source_cycles_observed'],'applied_events':len(groups),'applied_flips':len(events)}
def one(task,producer,plan):
 with slot() as lease:
  starts=B/'runtime/run_starts';starts.mkdir(exist_ok=True)
  with (B/'runtime/COUNT.lock').open('a+') as counter:
   fcntl.flock(counter,fcntl.LOCK_EX);state=r.snapshot(task['timeout_seconds']+5,1)
   assert state['CPU_global']<4143
   for key in ('program_binary','input','expected_stdout','schedule'):
    if task.get(key):checked(task[key])
   binary=checked(producer['binary']);script=checked(producer['config']);checked(producer['observer']);out=Path(task['output']);assert not out.exists()
   r.put(starts/(task['label']+'.json'),{'label':task['label'],'output':str(out),'phase':task['phase'],'plan':r.ref(plan),'started':now(),'reserved_cpu_seconds':task['timeout_seconds']+5})
  out.mkdir(parents=True,exist_ok=False);affinity=sorted(os.sched_getaffinity(0));assert len(affinity)>=32;cpu=affinity[lease]
  arguments=config.args(task['method'],task['program_binary']['path'],task['input']['path'] if task.get('input') else None,task.get('early',True),task.get('query_L',1),task['schedule']['path'] if task.get('schedule') else '')
  command=[str(binary),'--outdir='+str(out),str(script),*arguments,'--execute'];env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
  row={'label':task['label'],'phase':task['phase'],'method':task['method'],'program':task['program'],'status':'FAIL_RETAINED','cycles':None,'command':command,'host_core':cpu,'started':now(),'task':task,'producer':r.ref(B/'reports/PRODUCER_A2.lock.json')};start=time.perf_counter()
  try:
   with (out/'gem5.log').open('x') as log:
    result=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(out/'gem5.time'),'/usr/bin/prlimit','--core=0','--fsize=524288','--','/usr/bin/taskset','-c',str(cpu),'/usr/bin/timeout','--signal=TERM','--kill-after=3',str(task['timeout_seconds']),*command],stdout=log,stderr=subprocess.STDOUT,cwd=B,env=env,timeout=task['timeout_seconds']+20)
   row['exit_code']=result.returncode;row.update(validate(task,out,result.returncode));row['status']='PASS_PROGRAM_AND_FINITE_PROTOCOL_NOT_HARDWARE_QUALIFICATION'
  except Exception as exc:
   row['failure']=repr(exc);row['cycles']=None;(out/'validation_exception.txt').write_text(traceback.format_exc())
  row['host_cpu_seconds']=r.seconds(out/'gem5.time') if (out/'gem5.time').exists() and (out/'gem5.time').stat().st_size else None;row['wall_seconds']=time.perf_counter()-start;row['ended']=now();row['hashes']={p.name:r.sha(p) for p in out.iterdir() if p.is_file()};r.put(out/'EXECUTION.json',row)
  return row
def batch(name,tasks,workers=2):
 producer=prepare_producer();checked(producer['binary']);checked(producer['config']);checked(producer['observer']);source_lock_checked(producer['source_lock'])
 assert workers<=32 and 3531+len(list((B/'runtime/run_starts').glob('*.json')))+len(tasks)<=4143
 r.snapshot(sum(t['timeout_seconds']+5 for t in tasks),len(tasks))
 plan=B/'runtime/configs'/(name+'.lock.json');r.put(plan,{'status':'FROZEN_BEFORE_DISPATCH','tasks':tasks,'producer':r.ref(B/'reports/PRODUCER_A2.lock.json'),'authority':r.ref(r.AUTH),'workers':workers,'resources':r.snapshot()})
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:rows=list(pool.map(lambda task:one(task,producer,plan),tasks))
 good=all(x['status'].startswith('PASS_') for x in rows);r.put(B/'reports'/(name+'.json'),{'status':'PASS' if good else 'FAILURES_RETAINED','rows':rows,'plan':r.ref(plan),'resources':r.snapshot()})
 print(name,'PASS' if good else 'FAILURES_RETAINED',len(rows),flush=True);return good,rows
