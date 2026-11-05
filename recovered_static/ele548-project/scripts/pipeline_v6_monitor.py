"""Read current evidence and own processes; never dispatch or stop a job."""
from pipeline_v6_common import *
import time
F=ROOT/'rate_state_v5_pipeline/results';F.mkdir(exist_ok=True)
phases={}
for root,names in [(ROOT/'rate_state_v5/runtime_r5',['PERSISTENT_FAULT','EVALUATION_V3_FAULT']),
 (OUT,['CPU_GATE_BASE','CPU_GATE_FAULT','CLEAN_SCREEN','PILOT','EVALUATION_CLEAN','EVALUATION_FAULT'])]:
 for name in names:
  p=root/'reports'/(name+'.json')
  if root==OUT and name=='EVALUATION_FAULT':
   complete=OUT/'reports/EVALUATION_FAULT_COMPLETE.json'
   if complete.exists():p=complete
  if not p.exists():continue
  try:d=json.loads(p.read_text())
  except json.JSONDecodeError:continue
  phases[name]=dict(status=d['status'],completed=len(d.get('tasks',[])),planned=d.get('planned'),failures=sum(r['status']!='PASS' for r in d.get('tasks',[])))
  if root==OUT and name=='EVALUATION_FAULT' and p.name!='EVALUATION_FAULT_COMPLETE.json':
   suffix=OUT/'reports/EVALUATION_FAULT_REMAINDER.json'
   if suffix.exists():
    tail=json.loads(suffix.read_text())
    rows=d.get('tasks',[])+tail.get('tasks',[])
    phases[name].update(status='CONTINUATION_'+tail['status'],completed=len(rows),failures=sum(r['status']!='PASS' for r in rows))
   elif (OUT/'configs/EVALUATION_FAULT_CONTINUATION.lock.json').exists():
    phases[name]['status']='CONTINUATION_DECLARED'
active=[];proc={};build_roots=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  s=(p/'stat').read_text().split(') ',1)[1].split();args=(p/'cmdline').read_bytes().split(b'\0');cwd=(p/'cwd').resolve()
  proc[int(p.name)]=dict(parent=int(s[1]),seconds=(int(s[11])+int(s[12])+int(s[13])+int(s[14]))/os.sysconf('SC_CLK_TCK'))
  exe=(p/'exe').resolve()
  if exe in [ROOT/'third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.opt',BINARY]:
   active.append(dict(pid=int(p.name),producer='pipeline_v6' if exe==BINARY else 'R5',cpu_seconds=(int(s[11])+int(s[12]))/os.sysconf('SC_CLK_TCK')))
  if cwd==ROOT/'third_party/gem5-rate-pipeline-v6' and any(x.endswith(b'/scons') for x in args) and b'build/X86_PIPELINE/gem5.opt' in args:build_roots.append(int(p.name))
 except (OSError,ValueError,IndexError):continue
build=set(build_roots)
while True:
 nxt={pid for pid,s in proc.items() if s['parent'] in build};new=nxt-build
 if not new:break
 build.update(new)
build_active_seconds=sum(proc[p]['seconds'] for p in build)
recorded=global_cpu_seconds()/3600;active_hours=(sum(x['cpu_seconds'] for x in active)+build_active_seconds)/3600
counts=all_rows();new_count=sum(x.startswith('rate_state_v5_pipeline/') for x in counts)
d=dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),phases=phases,active_trials=active,
 active_new_build_processes=len(build),recorded_core_hours=recorded,active_unfinalized_core_hours=active_hours,
 approximate_core_hours_including_active=recorded+active_hours,new_recorded_core_hours=new_cpu_seconds()/3600,
 actual_distinct_cpu_records=len(counts),new_cpu_records=new_count,new_disk_gib=disk_gib(),
 limits=dict(global_core_hours=96,global_cpu_executions=2400,concurrent_simulations=8,new_pipeline_core_hours=12,new_pipeline_executions=185,new_disk_gib=20))
write(F/'LIVE_STATUS.json',d)
print(json.dumps(d,ensure_ascii=False))
