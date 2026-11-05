import argparse,csv,json,concurrent.futures
from continuation_common import *
from rng_namespace import rng,descriptor
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','main'],required=True);a=p.parse_args()
phase=a.phase;horizon=10000 if phase=='pilot' else 100000;n=4 if phase=='pilot' else 12
if phase=='main':
 prior=json.loads((OUT/'reports/G1_PILOT.json').read_text());assert prior['status']=='PASS';estimated=sum(t['host_cpu_seconds'] for t in prior['tasks'])*10*(1632/800)
 assert estimated<32*3600*.5,'G1 forecast would consume over half work cap'
 decision('G1','Expand diagnostic only after speed/equality gate.', ['G1_PILOT.json'],f'Projected main {estimated/3600:.3f} host core-hours; key arms only.','Run key-delay100k replay; all new owners are diagnostic development.')
windows=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())['workloads']
scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
words=scope['payload_words'];raw=next(w['site_ids'] for w in words if w['word_id']=='raw_path:0');path=next(w['site_ids'] for w in words if w['word_id']=='raw_path:1')
foldwords=[w for w in words if w['word_id'].startswith('folded:')]
out=OUT/f'reports/causal_{phase}';out.mkdir(parents=True,exist_ok=True);tasks=[];bound=[]
ages=[(0,4),(5,8),(9,14),(15,24),(25,43),(44,75),(76,129)]
for wi,name in enumerate(['SHORT-INT-1','SHORT-FP-1']):
 file=next(w for w in windows if w['workload']==name)['split_files']['design'];assert sha(ROOT/file['path'])==file['sha256']
 lines=[];serial=0
 for si,stratum in enumerate(['raw_direction','path','index_fold','tag_fold']):
  for trial in range(n):
   master=7131026+wi*1000000+si*10000+trial;lr=rng(master,'location');anchor=500000+serial*127;serial+=1
   bank=None;age=None
   if stratum=='raw_direction':lo,hi=ages[trial%7];age=int(lr.integers(lo,hi+1));site=raw[age]
   elif stratum=='path':site=path[int(lr.integers(len(path)))]
   else:
    bank=trial%7+1;row=0 if stratum=='index_fold' else trial%2+1
    ids=next(w['site_ids'] for w in foldwords if w['word_id']==f'folded:{bank}:{row}');site=ids[int(lr.integers(len(ids)))]
   owner=f'CONT_CAUSAL_DEV_V2_W{wi}_S{si}_N{trial}';variants=[('NONE',0,1)]
   if phase=='pilot':variants += [(arm,d,1) for arm in ['SHAM','H_ONLY','F_ONLY','HF','T_ONLY','FULL'] for d in [0,8,32,128]]
   else:variants += [(arm,d,1) for arm in ['H_ONLY','F_ONLY','HF','T_ONLY','HFT','HF_R','FULL'] for d in [0,128]];variants += [('NONE',0,0),('HF',128,0)]
   for arm,delay,learning in variants:
    label=f'{owner}_{arm}_D{delay}_L{learning}';lines.append(f'{label} {owner} {stratum} {site} {anchor} {delay} {arm} {learning} {horizon}\n')
    bound.append(dict(label=label,owner_id=owner,namespace='BPSEU_V2_CONTINUATION_CAUSAL_DEV_20261013_R1',phase='development_diagnostic',oracle=True,workload=name,input=file,anchor_conditional=anchor,delay_history_transitions=delay,site_id=site,stratum=stratum,raw_age=age,bank=bank,arm=arm,learning=learning,horizon_conditional=horizon,location_rng=descriptor(master,'location')))
 plan=out/f'{name}.bound.plan';plan.write_text(''.join(lines));tasks.append(dict(workload=name,command=[ROOT/'build/continuation_causal',ROOT/file['path'],plan,out/f'{name}.csv'],output=str((out/f'{name}.csv').relative_to(ROOT)),plan_sha256=sha(plan),input_sha256=file['sha256']))
write(OUT/f'configs/causal_{phase}.lock.json',dict(status='BOUND_EXECUTABLE_ORACLE_DIAGNOSTIC',cases=bound,base_owners=2*4*n,plans={t['workload']:t['plan_sha256'] for t in tasks},sampling='diagnostic equal role strata; not physical population weights',max_workers=2))
def run(t):
 r=timed(t['command'],out/f"{t['workload']}.log",timeout=3600);r.update(t);r['command']=list(map(str,t['command']));assert r['exit_code']==0,r
 with (ROOT/t['output']).open() as f:rows=list(csv.DictReader(f))
 assert len(rows)==len([b for b in bound if b['workload']==t['workload']]) and all(r['status']=='PASS' for r in rows)
 # Each unchanged SHAM must equal NONE for all logged algorithmic outcomes.
 if phase=='pilot':
  by={r['label']:r for r in rows}
  fields=['harm','help','net','prediction_divergences','provider_divergences','H_diff','P_diff','F_diff','T_diff','C_diff','R_diff']
  for row in rows:
   if row['arm']=='SHAM':ref=by[f"{row['owner']}_NONE_D0_L1"];assert all(row[k]==ref[k] for k in fields),'SHAM mismatch'
 r['CSV_sha256']=sha(ROOT/t['output']);r['replays']=len(rows);return r
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(run,tasks))
record=dict(status='PASS',phase=phase,oracle=True,base_owners=2*4*n,replays=len(bound),binary_sha256=sha(ROOT/'build/continuation_causal'),config_sha256=sha(OUT/f'configs/causal_{phase}.lock.json'),tasks=results,host_core_hours=sum(r['host_cpu_seconds'] for r in results)/3600)
write(OUT/f'reports/G1_{phase.upper()}.json',record);print(json.dumps({k:v for k,v in record.items() if k!='tasks'}))
