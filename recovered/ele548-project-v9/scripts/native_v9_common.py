"""Bounded V9 runs, actual answers and immutable attempt accounting."""
from pathlib import Path
import concurrent.futures,contextlib,datetime,fcntl,hashlib,json,os,re,resource,shutil,signal,subprocess,time
import v3_cpu_common as cpu
from v3_common import sha,write

ROOT=Path(__file__).resolve().parents[1]
OLD=Path('/home/youns/workspace/ele548-project')
OUT=ROOT/'rate_state_v9/runtime'
BINARY=ROOT/'third_party/gem5-native-v9/build/X86_PIPELINE/gem5.opt'
CONFIG=ROOT/'gem5/o3_native_v9.py'
IDS=['U','C_PAR_FREQUENT','C_PAR_PERIODIC','C_ECC','C_TMR','A_DIR']
V={
 'U':dict(scheme='P0',policy='LEGACY',k=0),
 'C_PAR_FREQUENT':dict(scheme='P_ED',policy='LEGACY',k=0),
 'C_PAR_PERIODIC':dict(scheme='P_ED',policy='N1',k=64),
 'C_ECC':dict(scheme='P_ECC',policy='LEGACY',k=0),
 'C_TMR':dict(scheme='P_TMR',policy='LEGACY',k=0),
 'A_DIR':dict(scheme='P0',policy='LEGACY',k=0),
}
PHASE_COUNTS={'GATE_NORMAL':6,'GATE_SBU':6,'GATE_DUE':6,'CLEAN':18,'DEVELOPMENT':72}
resource.setrlimit(resource.RLIMIT_CORE,(0,0))
for folder in ['configs','reports','inputs']:(OUT/folder).mkdir(parents=True,exist_ok=True)
def timed(command,log,timeout=1800,env=None,cwd=ROOT):
 log=Path(log);log.parent.mkdir(parents=True,exist_ok=True);assert not log.exists(),('IMMUTABLE_LOG',log)
 timing=log.with_suffix(log.suffix+'.time');start=time.perf_counter();timeout_group=None
 with log.open('w') as stream:
  proc=subprocess.Popen(['/usr/bin/time','-f','%U %S %M','-o',str(timing),*map(str,command)],cwd=cwd,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
  try:rc=proc.wait(timeout=timeout)
  except subprocess.TimeoutExpired:
   timeout_group=proc.pid
   try:os.killpg(proc.pid,signal.SIGTERM)
   except ProcessLookupError:pass
   try:proc.wait(timeout=3)
   except subprocess.TimeoutExpired:pass
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   proc.wait();rc=-999
 fields=timing.read_text().splitlines()[-1].split() if timing.exists() and timing.stat().st_size else []
 try:host_cpu=float(fields[0])+float(fields[1]);rss=int(fields[2])
 except (ValueError,IndexError):host_cpu=None;rss=None
 result=dict(exit_code=rc,wall_seconds=time.perf_counter()-start,host_cpu_seconds=host_cpu,max_rss_kib=rss,command=list(map(str,command)),log=str(log.relative_to(ROOT)))
 if timeout_group:
  result.update(timeout_process_group=timeout_group,group_terminated=True,resource_accounting_complete=False)
  write(log.with_suffix(log.suffix+'.timeout.json'),result)
 return result
cpu.timed=timed
def load(p):return json.loads(Path(p).read_text())
def ref(p):return dict(path=str(Path(p).relative_to(ROOT)),sha256=sha(p))
def note(name,observation,decision,next_action,**extra):
 with (OUT/'HYPOTHESIS_LOG.jsonl').open('a') as stream:
  stream.write(json.dumps(dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),hypothesis=name,observation=observation,decision=decision,next_action=next_action,**extra),ensure_ascii=False)+'\n')
def rows():
 result={}
 for p in (OUT/'reports').glob('*.json'):
  d=load(p)
  if not isinstance(d,dict):continue
  for r in d.get('tasks',[]):
   if r.get('output') and r.get('producer_binary_sha256'):result[r['output']]=r
 return result
def seconds(path):
 content=path.read_text().strip()
 if not content:return 0.
 verbose=re.search(r'User time \(seconds\):\s*([0-9.]+)',content);system=re.search(r'System time \(seconds\):\s*([0-9.]+)',content)
 if verbose and system:return float(verbose[1])+float(system[1])
 fields=content.splitlines()[-1].split()
 try:return float(fields[0])+float(fields[1])
 except (ValueError,IndexError):raise RuntimeError(('UNPARSEABLE_ACTUAL_TIME',str(path)))
def used_seconds():return sum(seconds(p) for p in (ROOT/'rate_state_v9').rglob('*.time'))
def disk_gib():return int(__import__('subprocess').check_output(['du','-sk',ROOT],text=True).split()[0])/1024**2
def budget_check(reserve=0):
 assert not list((OUT/'reports').rglob('*.timeout.json')),'UNRESOLVED_TIMEOUT_RESOURCE_ACCOUNTING'
 markers=list((OUT/'reports/run_starts').glob('*.json'))
 assert 3009+len(markers)+reserve<=3200,('GLOBAL_CPU_CAP',len(markers),reserve)
 assert len(markers)+reserve<=120,('FIRST_CHUNK_CAP',len(markers),reserve)
 assert 65.39845555555556+used_seconds()/3600<108,'GLOBAL_CORE_HOURS'
 assert used_seconds()<12*3600,'V9_CORE_HOURS'
 assert disk_gib()<8,'NEW_WORKTREE_DISK_8GIB'
 assert 20.54370880126953+disk_gib()<34,'COMBINED_DISK_34GIB'
 assert shutil.disk_usage(ROOT).free>=10*1024**3,'MIN_FREE_10GIB'
@contextlib.contextmanager
def slot():
 folder=OLD/'rate_state_v5/.cpu_slots';folder.mkdir(exist_ok=True);held=None
 while held is None:
  for index in range(32):
   f=(folder/f'{index}.lock').open('a+')
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);held=f;break
   except BlockingIOError:f.close()
  if held is None:time.sleep(.2)
 try:yield
 finally:fcntl.flock(held,fcntl.LOCK_UN);held.close()
def make(item,ident,phase,scenario='zero',owner='CONTROL',events='',audit=False,expected=None):
 v=V[ident];extra=['--pipeline-mode','native','--lookup-latency','0','--lookup-ii','0','--representation','direct' if ident=='A_DIR' else 'recurrent','--resource-mode','LEGACY']
 if audit:extra+=['--audit','--audit-limit','1000000']
 result=dict(input=item,program=item['name'],id=ident,phase=phase,scenario=scenario,owner=owner,label='.'.join([item['name'],scenario,owner,ident]),events_text=events,scheme=v['scheme'],policy=v['policy'],k=v['k'],C=0,U=0,additional_args=extra,max_ticks=250000000000)
 if expected is not None:result['expected_instructions']=expected
 return result
def verify_sources():
 d=load(OUT/'configs/source.lock.json')
 assert sha(CONFIG)==d['config_sha256'],'CONFIG_CHANGED'
 for name,digest in d['sources'].items():assert sha(ROOT/name)==digest,('SOURCE_CHANGED',name)
 for name,digest in d['transport'].items():assert sha(ROOT/'third_party/gem5-native-v9/src'/name)==digest,('TRANSPORT_CHANGED',name)
 assert sha(OUT/'configs/PRESERVED_V8.lock.json')==d['preservation_lock_sha256']
 return d
def declare():
 reference_path=OUT/'configs/EXPERIMENT_REFERENCES.lock.json'
 lineage=['sources/protection_scope.lock.json','reports/predictor_logical_state_manifest.jsonl','sources/public_workload_sources.lock.json']
 for name in lineage:assert sha(ROOT/name)==sha(OLD/name),('COMMON_SCOPE_OR_SOURCE_CHANGED',name)
 helpers=['scripts/v3_common.py','scripts/v3_cpu_common.py','scripts/run_o3_public_baseline.py','scripts/rng_namespace.py']+['scripts/native_v9_'+name+'.py' for name in ['common','gate','campaign','dispatch','analyze']]
 references={name:sha(ROOT/name) for name in lineage+helpers}
 ref_content=dict(status='EXPERIMENT_HELPERS_AND_MANDATORY_SCOPE_BEFORE_CPU',files=references)
 if reference_path.exists():assert load(reference_path)==ref_content,'EXPERIMENT_HELPER_CHANGED_AFTER_FREEZE'
 else:write(reference_path,ref_content)
 p=OUT/'configs/ROUND1.lock.json'
 d=dict(status='FIXED_BEFORE_ANY_V9_CPU',phase_counts=PHASE_COUNTS,planned_cpu=sum(PHASE_COUNTS.values()),chunk_cap=120,global_used_before=3009,global_cpu_cap=3200,global_core_hours_used_before=65.39845555555556,global_core_hours_cap=108,new_core_hours_cap=12,shared_slots=32,initial_pilot_slots=2,build_jobs=2,new_disk_gib=8,combined_disk_gib=34,variants=V,
  semantics='Native inline L0/II0 no finite journal; all normal check/vote/maintenance assumed within existing stage; repair4cycles for protected schemes. This is not measured ECC/TMR stage-fit or zero energy.',
  budget_precedence='V8 350/400 round closed with zero reservations. V9 own firstchunk108+12reserve fits remaining191 of currentglobal3200. Overlay2800/96 is stale; no cap increase/reset.',
  scenarios=['RAW130_SINGLE_SBU','WHOLE_K1_REF_SCALE1E15'],development_owners=2,development_master_base=9415480000,experiment_references=ref(reference_path),
  failure_policy='Retain every attempt/raw/failure/invalid pair. No failed cycles. Stop affectedstage after generic failures; decoder exceptions in WHOLE may be retained only by exact predeclared signatures.',
  selection='Development only on seen V8 inputs. No independent input holdout or best-tuned conventional claim. No-event/helpful/future events retained.')
 if p.exists():assert load(p)==d,'ROUND_CHANGED'
 else:write(p,d)
 return d
def run_one(t):
 with slot():
  start=datetime.datetime.now(datetime.timezone.utc).isoformat();marker=OUT/'reports/run_starts'/(t['phase']+'.'+t['label']+'.json');assert not marker.exists(),('DUPLICATE_ATTEMPT',marker)
  write(marker,dict(started_at=start,label=t['label'],phase=t['phase']))
  r=cpu.run_cpu(t);r.update(started_at=start,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
  if r['status']=='PASS':
   log=(ROOT/r['output']/'gem5.log').read_text()
   if re.search(r'instruction .*unimplemented|ignoring syscall|unimplemented syscall',log,re.I):r.update(status='FAIL_VALIDATION',failure='UNSUPPORTED_ISA_OR_SYSCALL')
   s=r['seu']
   if s.get('journal_accepted',0)!=s.get('journal_completed',0)+s.get('journal_cancelled',0)+s.get('journal_pending',0):r.update(status='FAIL_VALIDATION',failure='JOURNAL_CONSERVATION')
   if t.get('tape_horizon_ticks') and s['end_tick']>t['tape_horizon_ticks']:r.update(status='FAIL_VALIDATION',failure='EVENT_TAPE_HORIZON_EXCEEDED')
  if r['status']!='PASS':r['cycles']=None;r.setdefault('hashes',{}).update({p.name:sha(p) for p in (ROOT/r['output']).iterdir() if p.is_file() and p.name!='gem5.log.time'})
  return r
def execute(tasks,name,workers=32):
 eda=set()
 for process in Path('/proc').iterdir():
  if not process.name.isdigit():continue
  try:
   exe=(process/'exe').resolve();cwd=(process/'cwd').resolve()
   if exe.name in ['genus','innovus'] and cwd.is_relative_to(ROOT):eda.add(exe.name)
  except (OSError,RuntimeError):pass
 workers=min(workers,32-4*len(eda))
 declare();verify_sources();producer=load(OUT/'configs/BUILT_PRODUCER.pending.json');assert sha(BINARY)==producer['binary_sha256'] and sha(CONFIG)==producer['config_sha256']
 assert name in PHASE_COUNTS and len(tasks)==PHASE_COUNTS[name]
 report=OUT/'reports'/(name+'.json');lock=OUT/'configs'/(name+'.lock.json');assert not report.exists() and not lock.exists(),'IMMUTABLE_PHASE'
 write(lock,dict(status='FROZEN_BEFORE_DISPATCH',tasks=tasks,binary_sha256=sha(BINARY),config_sha256=sha(CONFIG),round_sha256=sha(OUT/'configs/ROUND1.lock.json')))
 cpu.OUT=OUT;cpu.BINARY=BINARY;cpu.CONFIG=CONFIG;result=[];offset=0
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  while offset<len(tasks):
   width=min(2 if offset==0 else workers,len(tasks)-offset);budget_check(width)
   batch=list(pool.map(run_one,tasks[offset:offset+width]));offset+=width;result.extend(batch)
   for r in batch:
    with (OUT/'EXPERIMENT_LEDGER.jsonl').open('a') as stream:stream.write(json.dumps({k:r.get(k) for k in ['phase','label','status','output','started_at','ended_at','host_cpu_seconds','max_rss_kib','command','failure']})+'\n')
    print(name,len(result),r['label'],r['status'],r.get('failure'),flush=True)
   failed=[r for r in result if r['status']!='PASS'];write(report,dict(status='FAIL_RETAINED' if failed else 'RUNNING',planned=len(tasks),tasks=result))
   if failed:raise RuntimeError(('FAILED_STAGE_RETAINED',name,[r['label'] for r in failed]))
   if len(result)==width:
    peak=max(r['max_rss_kib'] for r in result);available=next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'));assert peak*workers<available/2,'PILOT_MEMORY'
    write(OUT/'reports'/(name+'_PILOT_SPEED.json'),dict(status='PASS',actual_runs=width,mean_host_cpu_seconds=sum(r['host_cpu_seconds'] for r in result)/width,max_rss_kib=peak,authorized_workers=workers))
 write(report,dict(status='PASS',planned=len(tasks),tasks=result));return result
