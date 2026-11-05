"""V18 additive ledger; frozen prior cohorts, no mutation of legacy guards."""
from pathlib import Path
import hashlib,json,shutil,subprocess,sys
sys.dont_write_bytecode=True
BASE=Path(__file__).resolve().parents[1]
AUTH=BASE/'reports/BUDGET_AUTHORIZATION.lock.json'
def load(p):return json.loads(Path(p).read_text())
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def put(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def seconds(p):
 a=Path(p).read_text().strip().splitlines()[-1].split();return float(a[0])+float(a[1])
def snapshot(extra_seconds=0,extra_MiB=0):
 a=load(AUTH);assert a['authorized_by']=='user' and a['global_cpu_cap']==4143 and a['new_round_cpu_max']==612
 assert sha(a['proposal']['path'])==a['proposal']['sha256']
 old=a['prior_actual'];caps=a['caps'];starts=list((BASE/'runtime/run_starts').glob('*.json'))
 assert old['CPU_global']==3531 and not old['outstanding_reservations'] and len(starts)<=612
 active=0;reserved=0;active_paths=[]
 for p in starts:
  x=load(p);d=Path(x['output'])
  if not(d/'EXECUTION.json').exists():active+=1;reserved+=x['reserved_cpu_seconds'];active_paths.append(d)
 time_files=list((BASE/'runtime').rglob('*.time'))
 used=sum(seconds(p) for p in time_files if p.stat().st_size and not any(p.is_relative_to(d) for d in active_paths))
 charge=(used+reserved+extra_seconds)/3600
 size=int(subprocess.check_output(['du','-sk',str(BASE)],text=True).split()[0])/1024
 assert charge<=160 and old['recent_recorded_coreh']+charge<=168 and old['v9_onward_recorded_coreh']+charge<=179 and old['global_recorded_coreh']+charge<=252
 assert size+extra_MiB+active<=1024 and old['recent_MiB']+size+extra_MiB+active<=1536
 assert old['all7_GiB']+(size+extra_MiB+active)/1024<=10 and old['all7_GiB']+(size+extra_MiB+active)/1024+20.54370880126953<=34
 assert shutil.disk_usage(BASE).free>=10*1024**3
 return {'CPU_global':3531+len(starts),'CPU_new':len(starts),'CPU_cap':4143,'active':active,'round_recorded_coreh':used/3600,'reserved_coreh':reserved/3600,'round_disk_MiB':size,'recent_coreh':old['recent_recorded_coreh']+used/3600,'v9_coreh':old['v9_onward_recorded_coreh']+used/3600,'global_coreh':old['global_recorded_coreh']+used/3600,'recent_MiB':old['recent_MiB']+size,'all_physical_roots_GiB_conservative':old['all7_GiB']+size/1024,'accounting':'additive conservative namespace disk; all actual job.time files, active full timeouts; no baseline reset'}
