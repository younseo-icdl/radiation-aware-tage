import csv,concurrent.futures,json,subprocess,statistics
from continuation_common import *
from rng_namespace import rng,descriptor
import numpy as np
assert (OUT/'reports/G3_CORRECTNESS_2.log').read_text().startswith('PASS')
variants=[(s,s,'LEGACY',0) for s in ['P0','P_ED','P_ECC','P_TMR']]+[(f'N1_k{k}','P_ED','N1',k) for k in [1,8,32,64]]+[(f'H1_k{k}','P_ED','H1',k) for k in [8,32]]+[('H_REV','P_ED','REV',0)]
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());words=scope['payload_words'];sizes=np.array([len(w['site_ids']) for w in words]);ends=np.cumsum(sizes)
windows=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())['workloads'];out=OUT/'reports/cpp_screen';out.mkdir(parents=True,exist_ok=True)
for label,scheme,policy,k in variants:
 p=OUT/f'configs/manifest_{label}.json'
 if not p.exists():
  with p.open('w') as f:subprocess.run([ROOT/'build/continuation_manifest',policy,scheme],stdout=f,check=True)
jobs=[]
for wi,name in enumerate(['SHORT-INT-1','SHORT-FP-1']):
 file=next(w for w in windows if w['workload']==name)['split_files']['design'];assert sha(ROOT/file['path'])==file['sha256']
 groups=[('zero',0)]+[(s,n) for s in ['raw_direction','path','index_fold','tag_fold'] for n in range(3)]+[(m,n) for m in ['CHARM_6T','CHARM_8T','cluster12'] for n in range(2)]
 for gi,(scenario,n) in enumerate(groups):
  seed=1715480000+wi*1000000+gi*100+ n;tr=rng(seed,'time');kr=rng(seed,'K');lr=rng(seed,'location');events=[]
  if scenario in ['raw_direction','path','index_fold','tag_fold']:
   selected=[w for w in words if (scenario=='raw_direction' and w['word_id']=='raw_path:0') or (scenario=='path' and w['word_id']=='raw_path:1') or (scenario=='index_fold' and w['word_id'].startswith('folded:') and w['word_id'].endswith(':0')) or (scenario=='tag_fold' and w['word_id'].startswith('folded:') and not w['word_id'].endswith(':0'))]
   ids=sum([w['site_ids'] for w in selected],[]);events=[(float(tr.uniform(0,20000)),[ids[int(lr.integers(len(ids)))]])]
  elif scenario!='zero':
   t=0
   while True:
    t+=float(tr.exponential(1000))
    if t>=100000:break
    if scenario=='cluster12':
     ids=sum([w['site_ids'] for w in words],[]);anchor=int(lr.integers(len(ids)));event=[ids[(anchor+i)%len(ids)] for i in range(12)]
    else:
     total,p1=(214,205) if scenario=='CHARM_6T' else (147,142);K=1 if kr.integers(total)<p1 else 2
     ids=words[int(np.searchsorted(ends,int(lr.integers(346)),side='right'))]['site_ids'];anchor=int(lr.integers(len(ids)-K+1));event=ids[anchor:anchor+K]
    events.append((t,event))
  schedule=out/f'{name}.{scenario}.{n}.events';schedule.write_text(''.join(f'{t:.17g} '+ ';'.join(map(str,ids))+'\n' for t,ids in events))
  for label,scheme,policy,k in variants:
   prefix=out/f'{name}.{scenario}.{n}.{label}';cmd=[ROOT/'build/continuation_scheduled',ROOT/file['path'],'500000','100000',scheme,schedule,scenario,prefix,str(k),policy]
   jobs.append(dict(workload=name,scenario=scenario,trial=n,owner=f'CONT_CPP_DEV_V2_W{wi}_G{gi}_N{n}',seed=seed,variant=label,k=k,scheme=scheme,policy=policy,command=list(map(str,cmd)),output=str(prefix.relative_to(ROOT)),schedule_sha256=sha(schedule),input_sha256=file['sha256'],namespaces={r:descriptor(seed,r) for r in ['time','K','location']}))
write(OUT/'configs/cpp_screen.lock.json',dict(status='FROZEN_DESIGN_ONLY',jobs=jobs,variants=variants,selection_rule='equal-workload, equal single-role/repeat-family mean proxy20*net+checks+rebuild_steps; cost proxy not measuredCPU/PPA'))
def run(t):
 r=timed(t['command'],ROOT/(t['output']+'.log'),timeout=120);r.update(t)
 if r['exit_code']!=0:return dict(r,status='FAIL_EXECUTION')
 rows=list(csv.DictReader((ROOT/(t['output']+'.csv')).open()));assert len(rows)==1 and rows[0]['status']=='PASS';r.update(status='PASS',metrics=rows[0],CSV_sha256=sha(ROOT/(t['output']+'.csv')));return r
results=[]
path=OUT/'reports/G3_CPP_SCREEN.json'
def persist(status):write(path,dict(status=status,planned=len(jobs),completed=len(results),tasks=results,binary_sha256=sha(ROOT/'build/continuation_scheduled'),config_sha256=sha(OUT/'configs/cpp_screen.lock.json')))
for t in jobs[:2]:results.append(run(t));persist('RUNNING');assert results[-1]['status']=='PASS'
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for r in pool.map(run,jobs[2:]):results.append(r);persist('RUNNING')
assert all(r['status']=='PASS' for r in results);persist('PASS')
scores={}
for label,scheme,policy,k in variants:
 if policy not in ['N1','H1']:continue
 values=[]
 for name in ['SHORT-INT-1','SHORT-FP-1']:
  for scenario in ['raw_direction','path','index_fold','tag_fold','CHARM_6T','CHARM_8T','cluster12']:
   v=[r['metrics'] for r in results if r['variant']==label and r['workload']==name and r['scenario']==scenario]
   values.append(statistics.mean(20*int(x['net'])+int(x['checks'])+int(x['rebuild_steps']) for x in v))
 scores[label]=statistics.mean(values)
selection={family:min([label for label in scores if label.startswith(family)],key=lambda label:(scores[label],int(label.split('k')[-1]))) for family in ['N1','H1']}
write(OUT/'configs/policy_selection.lock.json',dict(status='CPP_DESIGN_SELECTED_BEFORE_NEW_CPU_OUTCOMES',selection=selection,scores=scores,design_report_sha256=sha(path),independence='old holdout is development context; new input/owners required for G5'))
decision('G3','Expected parity eliminates folded payload reductions; checked rebuild might avoid130refill.', ['G3_CPP_SCREEN.json','G3_CORRECTNESS_2.log'],f"{len(results)} actual design replays PASS; selected {selection} by frozen proxy rule.",'Run real O3 gates with finite queue and per-cycle rebuild; no oracle policies.')
print(selection,scores)
