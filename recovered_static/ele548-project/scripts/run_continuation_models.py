import csv,concurrent.futures
from continuation_common import *
c=json.loads((OUT/'configs/source_robustness.lock.json').read_text());jobs=c['jobs'];results=[];path=OUT/'reports/G5_SOURCE_ROBUSTNESS.json'
def persist(status):write(path,dict(status=status,planned=len(jobs),completed=len(results),tasks=results,config_sha256=sha(OUT/'configs/source_robustness.lock.json'),binary_sha256=sha(ROOT/'build/continuation_scheduled_final')))
def run(t):
 r=timed(t['command'],ROOT/(t['output']+'.log'),timeout=180);r.update(t)
 if r['exit_code']!=0:return dict(r,status='FAIL_EXECUTION')
 m=list(csv.DictReader((ROOT/(t['output']+'.csv')).open()));assert len(m)==1 and m[0]['status']=='PASS';assert int(m[0]['event_count'])==t['events'];assert int(m[0]['net'])==int(m[0]['harm'])-int(m[0]['help']);r.update(status='PASS',metrics=m[0],CSV_sha256=sha(ROOT/(t['output']+'.csv')));return r
persist('RUNNING')
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for start in range(0,len(jobs),2):
  assert budget_charge_seconds()<32*3600
  for r in pool.map(run,jobs[start:start+2]):results.append(r);persist('RUNNING')
assert all(r['status']=='PASS' for r in results);persist('PASS')
print('PASS',len(results),'actual source-pattern replays')
