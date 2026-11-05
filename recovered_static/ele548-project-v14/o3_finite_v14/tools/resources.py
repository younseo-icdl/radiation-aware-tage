#!/usr/bin/env python3
"""Actual count/time/disk ledger, with live CPU reservations charged fully."""
from pathlib import Path
import hashlib,json,shutil,subprocess
BASE=Path(__file__).resolve().parents[1];ROOT=BASE.parent
ROOTS=[Path('/home/youns/workspace/ele548-project-v'+str(i)) for i in range(9,15)]
OUT=BASE/'runtime/cpu_trials';APPROVAL=BASE/'reports/BUDGET_AMENDMENT_3513.lock.json'
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def seconds(p):
 v=Path(p).read_text().strip().splitlines()[-1].split();return float(v[0])+float(v[1])
def caps():
 default={'CPU':3487,'recent_coreh':2.5,'recent_MiB':192,'preparation_MiB':112,'approved':False}
 if not APPROVAL.exists():return default
 a=load(APPROVAL);assert a['authorized_by']=='user' and a['status']=='USER_AUTHORIZED_CPU3513_RECENT5H_320MIB'
 assert sha(a['proposal']['path'])==a['proposal']['sha256']
 assert a['CPU_cap']==3513 and a['recent_coreh_cap']==5 and a['recent_MiB_cap']==320
 return {'CPU':3513,'recent_coreh':5,'recent_MiB':320,'preparation_MiB':240,'approved':True}
def snapshot(additional_seconds=0,additional_MiB=0):
 cap=caps();v9,v10,v11,v12,v13,v14=ROOTS
 assert len(list((v9/'rate_state_v9').glob('**/reports/run_starts/*.json')))==352
 assert len(list((v10/'native_lifetime_next/runtime/reports/run_starts').glob('*.json')))==108
 assert len(list((v11/'overwrite_v11/runtime/cpu_regression/run_starts').glob('*.json')))==6
 assert len(list((v11/'overwrite_v11/runtime/cpu_fault_next/run_starts').glob('*.json')))==12
 starts=list((OUT/'run_starts').glob('*.json'));assert len(starts)<=26 and 3487+len(starts)<=cap['CPU']
 old=sum(seconds(p) for p in (v11/'overwrite_v11/runtime').rglob('*.time'))
 prior=sum(seconds(p) for d in [v12/'finite_source_v12/runtime',v13/'undo_packet_v13/runtime'] for p in d.rglob('*.time'))
 prep=sum(seconds(p) for p in (BASE/'runtime').rglob('*.time') if not p.is_relative_to(OUT));assert prior+prep<900,'PREPARATION_QUARTER_COREH'
 done=reserved=0;active=0
 for p in starts:
  marker=load(p);d=OUT/marker['label']
  if (d/'EXECUTION.json').exists() and (d/'gem5.time').exists():done+=seconds(d/'gem5.time')
  else:reserved+=marker['reserved_cpu_seconds'];active+=1
 total=old+prior+prep+done;charged=total+reserved+additional_seconds
 assert charged<cap['recent_coreh']*3600 and 11.171808333333335+charged/3600<16 and 76.57026388888889+charged/3600<108
 assert done+reserved+additional_seconds<3.5*3600,'V14_CPU_PHASE_3P5_COREH'
 sizes={str(p):int(subprocess.check_output(['du','-sk',str(p)],text=True).split()[0]) for p in ROOTS}
 prepMiB=sum(sizes[str(p)] for p in [v12,v13,v14])/1024;recentMiB=prepMiB+sizes[str(v11)]/1024;GiB=sum(sizes.values())/1048576
 assert prepMiB+additional_MiB+active<cap['preparation_MiB'] and recentMiB+additional_MiB+active<cap['recent_MiB']
 assert GiB+(additional_MiB+active)/1024<8 and GiB+(additional_MiB+active)/1024+20.54370880126953<34 and shutil.disk_usage(ROOT).free>=10*1024**3
 return {'CPU_global':3487+len(starts),'CPU_cap':cap['CPU'],'new_CPU':len(starts),'outstanding_reservations':active,'CPU_phase_recorded_coreh':done/3600,'inflight_reserved_coreh':reserved/3600,'recent_recorded_coreh':total/3600,'v9_onward_recorded_coreh':11.171808333333335+total/3600,'global_recorded_coreh':76.57026388888889+total/3600,'preparation_recorded_coreh':(prior+prep)/3600,'preparation_MiB':prepMiB,'recent_MiB':recentMiB,'all6_GiB':GiB,'caps':cap}
if __name__=='__main__':print(json.dumps(snapshot(),indent=2))
