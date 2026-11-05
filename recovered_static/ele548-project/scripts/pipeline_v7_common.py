"""Isolated v6 execution; shared eight leases and the original global budgets."""
from pathlib import Path
import concurrent.futures,datetime,json,os,shutil,subprocess
import v5_common as old
from v5_common import ROOT,sha,write,timed,trial_slot,task
import v3_cpu_common as cpu
OUT=ROOT/'rate_state_v5_pipeline_v7/runtime'
BINARY=ROOT/'third_party/gem5-rate-pipeline-v6/build/X86_PIPELINE/gem5.opt'
CONFIG=ROOT/'gem5/o3_pipeline_v7.py'
for sub in ['configs','reports','inputs','sources']:(OUT/sub).mkdir(parents=True,exist_ok=True)
def all_rows():
 rows={}
 for root in [ROOT/'rate_state_v5',ROOT/'rate_state_v5_pipeline_v7']:
  for folder in root.glob('runtime*'):
   for p in (folder/'reports').glob('*.json'):
    try:d=json.loads(p.read_text())
    except (OSError,json.JSONDecodeError):continue
    if not isinstance(d,dict):continue
    for r in d.get('tasks',[]):
     if isinstance(r,dict) and r.get('producer_binary_sha256') and r.get('output'):rows[r['output']]=r
 return rows
def new_cpu_seconds():
 total=0.
 for p in OUT.rglob('*.time'):
  try:v=p.read_text().splitlines()[-1].split();total+=float(v[0])+float(v[1])
  except (ValueError,IndexError):pass
 return total
def global_cpu_seconds():return old.used_cpu()+new_cpu_seconds()
def disk_gib():
 paths=['rate_state_v5','build/v5_producers','third_party/gem5-rate-state-v5','rate_state_v5_pipeline_v7','third_party/gem5-rate-pipeline-v6']
 return sum(int(x.split()[0]) for x in subprocess.check_output(['du','-sk',*paths],cwd=ROOT,text=True).splitlines())/1024**2
def verify_sources():
 lock=OUT/'configs/source.lock.json';d=json.loads(lock.read_text());target=ROOT/'third_party/gem5-rate-pipeline-v6'
 for name,digest in d['sources'].items():assert sha(ROOT/name)==digest,('SOURCE_CHANGED',name)
 for name,digest in d['transport'].items():assert sha(target/'src'/name)==digest,('TRANSPORT_CHANGED',name)
 assert sha(target/'src/SConscript')==d['upstream_opt_sconscript_sha256'],'BUILD_FLAGS_CHANGED'
 for p in (ROOT/'gem5_rate_pipeline_v7_ext').iterdir():
  if p.is_file():assert sha(p)==sha(target/'src/cpu/pred'/p.name),('COPIED_EXTENSION_MISMATCH',p.name)
 parent=ROOT/'rate_state_v5/runtime_r5/configs/source.lock.json';assert sha(parent)==d['base_R5_source_lock_sha256']
 for name,digest in json.loads(parent.read_text())['sources'].items():assert sha(ROOT/name)==digest,('REUSED_SOURCE_CHANGED',name)
 for name,digest in json.loads((OUT/'configs/PRESERVED_V5.lock.json').read_text())['hashes'].items():assert sha(ROOT/name)==digest,('OLD_PRODUCER_CHANGED',name)
 return d
def budget_check(additional=0):
 rows=all_rows();new=sum(k.startswith('rate_state_v5_pipeline_v7/') for k in rows)
 assert len(rows)+additional<=2400,('GLOBAL_CPU_COUNT',len(rows),additional)
 assert new+additional<=185,('NEW_CPU_COUNT',new,additional)
 assert global_cpu_seconds()<96*3600,('GLOBAL_CORE_HOURS',global_cpu_seconds()/3600)
 assert new_cpu_seconds()<12*3600,('NEW_CORE_HOURS',new_cpu_seconds()/3600)
 assert disk_gib()<20,('GLOBAL_NEW_DISK_GIB',disk_gib())
 assert shutil.disk_usage(ROOT).free>=10*1024**3,'MIN_FREE_DISK_10GIB'
def variant(mode='pipeline',rep='recurrent',L=1):
 return ['--pipeline-mode',mode,'--representation',rep,'--pipeline-latency',str(L),'--pipeline-ii','1']
def make(item,ident,phase,scenario='zero',owner='CONTROL',event='',mode='pipeline',rep='recurrent',L=1,extra=None,expected=None):
 t=task(item,ident,phase,scenario,owner,event,extra=variant(mode,rep,L)+(extra or []))
 if expected:t['expected_instructions']=expected
 return t
def run_one(t):
 with trial_slot():
  started=datetime.datetime.now(datetime.timezone.utc).isoformat()
  marker=OUT/'reports/run_starts'/f"{t['phase']}.{t['label']}.json"
  assert not marker.exists(),marker
  write(marker,dict(started_at=started,label=t['label']))
  r=old._run_cpu(t)
  r.update(started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
  if r['status']=='PASS':
   s=r['seu']
   if s.get('pipeline_enabled'):
    if s['pipeline_accepted']!=s['pipeline_consumed']+s['pipeline_cancelled']+s['pipeline_pending']:
     r.update(status='FAIL_VALIDATION',failure='PIPELINE_CONSERVATION')
  return r
def execute(tasks,name,workers=2,allowed_failures=()):
 cpu.OUT=OUT;cpu.BINARY=BINARY;cpu.CONFIG=CONFIG
 lock=OUT/'configs/PRODUCER.lock.json';pending=OUT/'configs/BUILT_PRODUCER.pending.json'
 producer=json.loads((lock if lock.exists() else pending).read_text())
 assert sha(BINARY)==producer['binary_sha256'] and sha(CONFIG)==producer['config_sha256'],'PRODUCER_MUTATED'
 verify_sources();assert sha(OUT/'configs/source.lock.json')==producer['source_lock_sha256'],'STALE_SOURCE_LOCK'
 binding=OUT/'configs/BUILD_2_BINDING.json';assert sha(binding)==producer['build_binding_sha256'],'STALE_BUILD_BINDING'
 report=OUT/'reports'/(name+'.json');task_lock=OUT/'configs'/(name+'.lock.json')
 content=dict(status='FROZEN_BEFORE_DISPATCH',tasks=tasks,binary_sha256=sha(BINARY),config_sha256=sha(CONFIG))
 rows=[]
 if report.exists():
  d=json.loads(report.read_text());assert d['status']=='RUNNING','IMMUTABLE_TERMINAL_REPORT'
  assert json.loads(task_lock.read_text())==content,'RESUME_FROZEN_TASK_MISMATCH'
  rows=d['tasks']
  for i,r in enumerate(rows):assert r['label']==tasks[i]['label'] and r['producer_binary_sha256']==producer['binary_sha256']
 else:
  if task_lock.exists():assert json.loads(task_lock.read_text())==content
  else:write(task_lock,content)
 start=len(rows)
 with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
  while start<len(tasks):
   width=min(workers,2) if start==0 else workers
   width=min(width,len(tasks)-start);budget_check(width)
   batch=list(pool.map(run_one,tasks[start:start+width]));start+=width
   failed=[]
   for r in batch:
    rows.append(r)
    with (OUT/'EXPERIMENT_LEDGER.jsonl').open('a') as f:f.write(json.dumps({k:r.get(k) for k in ['label','status','started_at','ended_at','command','host_cpu_seconds','wall_seconds','max_rss_kib','output','producer_binary_sha256','failure']})+'\n')
    print(name,len(rows),r['label'],r['status'],r.get('failure'),flush=True)
    if r['status']!='PASS':
     log=(ROOT/r['output']/'gem5.log').read_text(errors='replace')
     if not allowed_failures or not any(x in log for x in allowed_failures):failed.append(r)
   write(report,dict(status='FAIL_RETAINED' if failed else 'RUNNING',tasks=rows,planned=len(tasks)))
   if failed:raise RuntimeError('Failed new CPU stage retained; no further dispatch')
   if start==width:
    peak=max(r.get('max_rss_kib') or 0 for r in rows)
    available=next(int(s.split()[1]) for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:'))
    assert peak*workers<available/2,'PILOT_MEMORY_GATE'
    mean=sum(r['host_cpu_seconds'] for r in rows)/len(rows)
    write(OUT/'reports'/(name+'_PILOT_SPEED.json'),dict(status='PASS',actual_runs=len(rows),max_rss_kib=peak,
     mean_host_cpu_seconds=mean,remaining_phase_cpu_seconds_forecast=(len(tasks)-len(rows))*mean,forecast_is_not_measured=True))
 write(report,dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'COMPLETED_WITH_FAILED_RUNS',tasks=rows,planned=len(tasks),
  recorded_global_core_hours=global_cpu_seconds()/3600,new_core_hours=new_cpu_seconds()/3600))
 return rows
