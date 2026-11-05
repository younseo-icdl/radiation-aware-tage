"""Predeclared 1k/10k/100k windows using observation-only C++ instrumentation."""
import json,csv,concurrent.futures
from v3_common import *
cfg=json.loads((OUT/'configs/B_functional.lock.json').read_text());jobs=[]
for t in cfg['jobs']:
 cmd=t['command'].copy();cmd[0]=str(ROOT/'build/v3_window_probe');cmd[3]='104096'
 prefix=OUT/'reports/B_windows'/Path(t['output']).name;cmd[7]=str(prefix)
 jobs.append(dict(t,command=cmd,output=str(prefix.relative_to(ROOT)),role='functional horizon diagnostic, original source controllers; H1 no-lag reference, not asynchronous D',requested_postevent_conditionals=[1000,10000,100000]))
write(OUT/'configs/B_WINDOWS.lock.json',dict(status='FROZEN_BEFORE_WINDOW_OUTCOMES',jobs=jobs,binary_sha256=sha(ROOT/'build/v3_window_probe'),observation_source_sha256=sha(ROOT/'src/costaware_v3_roundb/window_probe.cpp'),event_coordinate=4096,seen_design_owners=True))
def run(t):
 r=timed(t['command'],ROOT/(t['output']+'.log'));r.update(t);r['status']='FAIL_EXECUTION'
 if r['exit_code']==0:
  m=list(csv.DictReader((ROOT/(t['output']+'.csv')).open()));w=list(csv.DictReader((ROOT/(t['output']+'.windows.csv')).open()));assert len(m)==1 and m[0]['status']=='PASS'
  assert len(w)==3 and all(int(x['observed_conditionals'])==int(x['requested_postevent_conditionals']) and x['right_censored']=='0' and int(x['net'])==int(x['harm'])-int(x['help']) for x in w)
  r.update(status='PASS',metrics=m[0],windows=w,hashes={p.name:sha(p) for p in (ROOT/t['output']).parent.glob((ROOT/t['output']).name+'*') if p.is_file()})
 return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:rows=list(pool.map(run,jobs))
write(OUT/'reports/B_WINDOWS.json',dict(status='PASS' if all(r['status']=='PASS' for r in rows) else 'FAIL_RETAINED',planned=len(jobs),completed=len(rows),tasks=rows))
print('Actual complete 1k/10k/100k windows',len(rows),'failed',sum(r['status']!='PASS' for r in rows))
