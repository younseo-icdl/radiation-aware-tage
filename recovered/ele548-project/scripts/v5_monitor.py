"""Read-only evidence status and budget checkpoints; no dispatch or daemon."""
from v5_common import ROOT,write,used_cpu,sha
import json,subprocess,datetime,os
F=ROOT/'rate_state_v5/results';F.mkdir(exist_ok=True)
phases=['SOURCE','WHOLE','SHORT_CONTROL','METADATA','PERSISTENT_CLEAN','PERSISTENT_FAULT','EVALUATION_V3_CLEAN','EVALUATION_V3_FAULT']
R=ROOT/'rate_state_v5/runtime_r5';rs=[]
for phase in phases:
 p=R/'reports'/(phase+'.json')
 if p.exists():
  try:d=json.loads(p.read_text())
  except json.JSONDecodeError:continue
  rs.append(dict(phase=phase,status=d['status'],completed=len(d.get('tasks',[])),planned=d.get('planned'),failed=sum(x['status']!='PASS' for x in d.get('tasks',[]))))
 else:rs.append(dict(phase=phase,status='NOT_DISPATCHED_OR_WAITING'))
paths=['rate_state_v5','third_party/gem5-rate-state-v5','build/v5_producers']
du=subprocess.check_output(['du','-sk',*paths],cwd=ROOT,text=True)
disk=sum(int(x.split()[0]) for x in du.splitlines())/1024**2
cpu=used_cpu()/3600
active=[]
for line in subprocess.check_output(['ps','-C','gem5.opt','-o','pid='],text=True).splitlines():
 pid=int(line)
 try:
  proc=ROOT/f'/proc/{pid}';exe=(proc/'exe').resolve()
  if exe!=ROOT/'third_party/gem5-rate-state-v5/build/X86_STAGE0/gem5.opt':continue
  stat=(proc/'stat').read_text().split();seconds=(int(stat[13])+int(stat[14]))/os.sysconf('SC_CLK_TCK')
  active.append(dict(pid=pid,actual_cpu_seconds_so_far=seconds))
 except (FileNotFoundError,ProcessLookupError):pass
active_hours=sum(p['actual_cpu_seconds_so_far'] for p in active)/3600
write(F/'LIVE_STATUS.json',dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),phases=rs,
 recorded_host_core_hours=cpu,active_trials=active,active_unfinalized_core_hours=active_hours,
 approximate_core_hours_including_active=cpu+active_hours,new_disk_gib=disk,limits=dict(core_hours=96,new_disk_gib=20,cpu_trials=2400),
 accounting='Recorded child CPU from .time, excluding unmetered Python orchestration/audits. New disk includes full copied build/worktree and superseded binary snapshots.',
 hardware='No RTL/PDK; no fully qualified new hardware candidate because metadata adverse tests fail.'))
for mark in [32,64]:
 checkpoint=F/f'CHECKPOINT_{mark}_CORE_HOURS.json'
 if cpu>=mark and not checkpoint.exists():
  write(checkpoint,dict(status='REPORT_CHECKPOINT_CONTINUE_WITHIN_96_CORE_HOURS',threshold=mark,
    recorded_core_hours=cpu,active_unfinalized_core_hours=active_hours,phases=rs,
    user_permission_wait=False,reason='Predeclared intermediate checkpoint, not a stop/approval boundary.'))
lines=['# 이어받기 상태','',f'기록 시각: {datetime.datetime.now(datetime.timezone.utc).isoformat()}',f'완료 기록 child CPU: {cpu:.3f}/96 core-hours. 현재{len(active)}개 실행의 미확정 CPU: {active_hours:.3f} core-hours. 새 디스크: {disk:.3f}/20 GiB.','',
'독립 평가의 predictor/입력/owner는 동결돼 있다. 기존 실행을 중복 dispatch하지 말고 LIVE_STATUS.json과 실제 프로세스를 먼저 확인한다. SOURCE/WHOLE/SHORT_CONTROL은 완료 prefix를 검증하고 재개할 수 있다. 원본 EVALUATION_CLEAN과 첫 호환 수정 V2의 실패를 보존하고, binary64+integer I/O의 별도 workload를 V3로 평가한다.','','|단계|상태|완료|계획|실패|','|---|---|---:|---:|---:|']
for r in rs:lines.append(f"|{r['phase']}|{r['status']}|{r.get('completed','')}|{r.get('planned','')}|{r.get('failed','')}|")
lines+=['','다음: 모든 필수 cohort가 terminal이면 `scripts/v5_analyze_cpu.py`, `scripts/v5_lifetime_summary.py`, final reporting/audit/package를 실행한다. HDL 앞에서 멈춘다.','',
'orchestration 중단 이력: STATE_PROFILE의 top-level JSON list를 dict로 처리하던 집계기 오류를 수정했다. 완료된 prefix는 재실행하지 않았다. 원본 logs와 namespace를 유지했다.']
(F/'RESUME.ko.md').write_text('\n'.join(lines)+'\n')
print(json.dumps(dict(recorded_core_hours=round(cpu,3),active_trials=len(active),active_unfinalized_core_hours=round(active_hours,3),approximate_core_hours_including_active=round(cpu+active_hours,3),new_disk_gib=round(disk,3),phases=rs),ensure_ascii=False))
