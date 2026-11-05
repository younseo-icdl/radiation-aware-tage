"""Real HW1-derived streams, disjoint V5 event owners, no predictor tuning oracle."""
from v5_common import *
from rng_namespace import rng,descriptor
import argparse,csv,subprocess

p=argparse.ArgumentParser();p.add_argument('--phase',choices=['pilot','development','refinement','extended'],required=True);a=p.parse_args()
phase=a.phase
names=['SHORT-INT-1','SHORT-FP-1','SHORT-MM-1','SHORT-SERV-1','LONG-SPEC2K6-00','LONG-SPEC2K6-01']
if phase=='pilot':names=names[:1]
modes=['recurrent','direct'] if phase=='pilot' else ['recurrent','direct','geometric','stratum','short32']
if phase=='refinement':modes=['geometric','stratum']
if phase=='extended':modes=['recurrent','direct']
owners=2 if phase=='pilot' else 8
H=300000 if phase=='extended' else 100000
tap_budget=16 if phase=='refinement' else 8
manifest=[json.loads(line) for line in (ROOT/'reports/predictor_logical_state_manifest.jsonl').read_text().splitlines()]
out=OUT/'reports'/f'CPP_{phase}';out.mkdir(parents=True,exist_ok=False)
tasks=[]
for wi,name in enumerate(names):
    trace=ROOT/f'workloads/derived/e1/{name}.design.bin'
    for mode in modes:
        fields=['raw','path','table']+(['fold'] if mode in ['recurrent','short32'] else [])
        plan=[];seeds=[]
        for fi,field in enumerate(fields):
            candidates=[s for s in manifest if (field=='raw' and s['field']=='raw_path' and s['bank']==0 and s['row']<32) or (field=='path' and s['field']=='raw_path' and s['bank']==1) or (field=='fold' and s['field']=='folded') or (field=='table' and s['field']=='ctr')]
            # Short-history raw population ends 98 bits earlier. Table sites and
            # path/fold logical identifiers are re-enumerated for that geometry.
            for owner in range(owners):
                master=3155480000+wi*1000000+['raw','path','table','fold'].index(field)*10000+owner
                loc=rng(master,'location');when=rng(master,'time');s=candidates[int(loc.integers(len(candidates)))];site=s['site_id']
                if mode=='short32' and (s['field']=='folded' or (s['field']=='raw_path' and s['bank']==1)):site-=98
                inject=int(when.integers(1000,10000));plan.append(f'{owner} {inject} {field} {site}\n')
                seeds.append(dict(owner=owner,field=field,master=master,time=descriptor(master,'time'),location=descriptor(master,'location'),site=site,inject=inject))
        pp=out/f'{name}.{mode}.plan';pp.write_text(''.join(plan));result=out/f'{name}.{mode}.csv'
        tasks.append(dict(name=name,mode=mode,trace=str(trace.relative_to(ROOT)),trace_sha256=sha(trace),plan=str(pp.relative_to(ROOT)),plan_sha256=sha(pp),seeds=seeds,result=str(result.relative_to(ROOT)),
            command=list(map(str,[ROOT/'build/v5_replay',trace,mode,str(tap_budget),str(H),pp,result,'50000']))))
write(OUT/'configs'/f'CPP_{phase}.lock.json',dict(status='FROZEN_BEFORE_EXECUTION',tasks=tasks,source_sha256=sha(ROOT/'src/rate_state_v5/representation.hpp'),binary_sha256=sha(ROOT/'build/v5_replay'),
    event_time='uniform conditional ordinal diagnostic, not uniform physical time',no_fold_injection_into_direct=True))
def run(t):
    r=timed(t['command'],out/f"{t['name']}.{t['mode']}.log",timeout=1800)
    assert r['exit_code']==0,r
    rows=list(csv.DictReader((ROOT/t['result']).open()));assert rows and all(x['status']=='PASS' for x in rows),t['result']
    r.update(name=t['name'],mode=t['mode'],trials=len(rows),result=t['result'],clean=json.loads((out/f"{t['name']}.{t['mode']}.log").read_text().splitlines()[-1]))
    return r
rows=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=2 if phase=='pilot' else 8) as pool:
    for r in pool.map(run,tasks):
        rows.append(r);write(OUT/'reports'/f'CPP_{phase}.json',dict(status='RUNNING',tasks=rows))
        print(phase,len(rows),r['name'],r['mode'],r['trials'],r['host_cpu_seconds'],flush=True)
write(OUT/'reports'/f'CPP_{phase}.json',dict(status='PASS',tasks=rows,completed_replays=sum(r['trials'] for r in rows)))
note('B1.'+phase,'TESTED_RESULT',f"Completed {sum(r['trials'] for r in rows)} real trace conditional trials",'Analyze matched raw lifetime and absolute clean MPKI','CPU equivalence and finite lookup sensitivity')
