#!/usr/bin/env python3
"""Strict prospective CPU18 ledger; no authority inferred from this code."""
from pathlib import Path
import importlib.util,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
import prepare as m
BASE=m.BASE;OUT=BASE/'runtime/cpu_trials';AUTH=BASE/'reports/CPU_AUTHORIZATION.lock.json'
def load(p):return json.loads(Path(p).read_text())
def seconds(p):return m.seconds(Path(p))
def snapshot(additional_seconds=0,additional_MiB=0):
 s=importlib.util.spec_from_file_location('old_cpu_resources',m.V14/'tools/resources_followon.py');oldmod=importlib.util.module_from_spec(s);s.loader.exec_module(oldmod);old=oldmod.snapshot()
 assert old['new_CPU']==24 and old['outstanding_reservations']==0,'V14_FROZEN_COHORT_CHANGED'
 approved=AUTH.exists()
 if approved:
  auth=load(AUTH);assert auth['authorized_by']=='user' and auth['status']=='USER_AUTHORIZED_CPU3531_RECENT8_V9_19'
  assert auth['CPU_cap']==3531 and auth['recent_coreh_cap']==8 and auth['v9_onward_coreh_cap']==19 and auth['CPU_phase_coreh_cap']==4
  assert m.sha(auth['proposal']['path'])==auth['proposal']['sha256']
  caps={'CPU':3531,'recent_coreh':8,'v9_coreh':19,'phase_coreh':4,'approved':True}
 else:caps={'CPU':3513,'recent_coreh':5,'v9_coreh':16,'phase_coreh':0,'approved':False}
 prep_seconds=sum(seconds(p) for p in (BASE/'runtime').rglob('*.time') if not p.is_relative_to(OUT))
 assert old['preparation_recorded_coreh']+(prep_seconds/3600)<.25
 starts=list((OUT/'run_starts').glob('*.json'));assert len(starts)<=20
 done=reserved=0;active=0
 for p in starts:
  marker=load(p);d=OUT/marker['label']
  if (d/'EXECUTION.json').exists() and (d/'gem5.time').exists():done+=seconds(d/'gem5.time')
  else:reserved+=marker['reserved_cpu_seconds'];active+=1
 if not approved:assert not starts and additional_seconds==0,'CPU18_NEEDS_USER_BUDGET_AMENDMENT'
 charged=(prep_seconds+done+reserved+additional_seconds)/3600
 assert 3511+len(starts)<=caps['CPU'] and (done+reserved+additional_seconds)/3600<=caps['phase_coreh']
 assert old['recent_recorded_coreh']+charged< caps['recent_coreh'] and old['v9_onward_recorded_coreh']+charged<caps['v9_coreh'] and old['global_recorded_coreh']+charged<108
 size=int(subprocess.check_output(['du','-sk',str(m.ROOT)],text=True).split()[0])/1024
 cpu_size=int(subprocess.check_output(['du','-sk',str(OUT)],text=True).split()[0])/1024 if OUT.exists() else 0
 # Trial output is excluded only from the preparation-only sublimit. Every
 # byte remains charged to the320MiB recent aggregate and the8GiB all-root cap.
 assert old['preparation_MiB']+size-cpu_size<240
 assert old['recent_MiB']+size+additional_MiB+active<320 and old['all6_GiB']+(size+additional_MiB+active)/1024<8
 assert old['all6_GiB']+(size+additional_MiB+active)/1024+20.54370880126953<34 and shutil.disk_usage(m.ROOT).free>=10*1024**3
 return {'CPU_global':3511+len(starts),'CPU_new':len(starts),'CPU_cap':caps['CPU'],'outstanding_reservations':active,'phase_recorded_coreh':done/3600,'reserved_coreh':reserved/3600,'preparation_coreh':old['preparation_recorded_coreh']+prep_seconds/3600,'recent_recorded_coreh':old['recent_recorded_coreh']+(prep_seconds+done)/3600,'v9_onward_recorded_coreh':old['v9_onward_recorded_coreh']+(prep_seconds+done)/3600,'global_recorded_coreh':old['global_recorded_coreh']+(prep_seconds+done)/3600,'preparation_MiB':old['preparation_MiB']+size-cpu_size,'CPU_output_MiB':cpu_size,'recent_MiB':old['recent_MiB']+size,'all7_GiB':old['all6_GiB']+size/1024,'caps':caps}
if __name__=='__main__':print(json.dumps(snapshot(),indent=2))
