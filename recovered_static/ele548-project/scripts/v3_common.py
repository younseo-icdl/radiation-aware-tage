"""Separate v3 evidence namespace and conservative round accounting."""
import hashlib,json,subprocess,time,datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'continuation_v3/runtime'
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def write(p,x):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+'.tmp');t.write_text(json.dumps(x,indent=2,ensure_ascii=False)+'\n');t.replace(p)
def decision(stage,hypothesis,evidence,outcome,next_action,assumptions=None,falsifier=None,expense=None):
 with (OUT/'decision_log.jsonl').open('a') as f:f.write(json.dumps(dict(stage=stage,time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),hypothesis=hypothesis,evidence_paths=evidence,outcome=outcome,next_action=next_action,assumptions=assumptions,falsifier=falsifier,expense=expense),ensure_ascii=False)+'\n')
def timed(command,log,timeout=1800,env=None,cwd=ROOT):
 log=Path(log);log.parent.mkdir(parents=True,exist_ok=True);timing=log.with_suffix(log.suffix+'.time');start=time.perf_counter()
 assert not log.exists(),'immutable output already exists: '+str(log)
 with log.open('w') as f:
  try:p=subprocess.run(['/usr/bin/time','-f','%U %S %M','-o',str(timing)]+list(map(str,command)),cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout);rc=p.returncode
  except subprocess.TimeoutExpired:rc=-999
 vals=timing.read_text().splitlines()[-1].split() if timing.exists() and timing.stat().st_size else []
 try:cpu=float(vals[0])+float(vals[1]);rss=int(vals[2])
 except (IndexError,ValueError):cpu=None;rss=None
 return dict(exit_code=rc,wall_seconds=time.perf_counter()-start,host_cpu_seconds=cpu,max_rss_kib=rss,command=list(map(str,command)),log=str(log.relative_to(ROOT)))
def used_cpu():
 total=0
 for p in OUT.rglob('*.time'):
  try:v=p.read_text().splitlines()[-1].split();total+=float(v[0])+float(v[1])
  except (ValueError,IndexError):pass
 return total
