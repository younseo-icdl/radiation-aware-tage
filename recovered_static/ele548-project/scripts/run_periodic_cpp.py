#!/usr/bin/env python3
"""Finite design pilot and proxy policy selection; baseline source/results immutable."""
import concurrent.futures
import csv
import json
import subprocess
import time
from pathlib import Path
import numpy as np
from rng_namespace import rng, descriptor
from summarize_e3_cpu import sha

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'configs/periodic_extension.lock.json'

def main():
    c=json.loads(CONFIG.read_text())
    assert sha(ROOT/'sources/protection_scope.lock.json')==c['scope_sha256']
    assert (ROOT/'reports/periodic_extension/cpp_correctness.log').read_text().startswith('PASS')
    scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
    variants=[(s,s,0) for s in c['required_baselines']]+[(f'P_PERIODIC_ED_k{k}','P_ED',k) for k in c['candidate_intervals']]
    windows={w['workload']:w for w in json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())['workloads']}
    out=ROOT/'reports/periodic_extension/cpp_design';out.mkdir(parents=True,exist_ok=True)
    tasks=[]
    for wi,name in enumerate(c['cpp_design_workloads']):
        file=windows[name]['split_files']['design'];assert sha(ROOT/file['path'])==file['sha256']
        groups=[('zero','mixed',0,c['cpp_design_seed_base']+wi*1000000)]
        groups += [('single',field,n,c['cpp_design_seed_base']+wi*1000000+fi*10000+n) for fi,field in enumerate(c['single_fields']) for n in range(c['cpp_single_trials_per_field'])]
        groups += [('repeat','mixed',n,c['cpp_design_seed_base']+wi*1000000+60000+n) for n in range(c['cpp_repeat_trials'])]
        for mode,field,n,seed in groups:
            tr=rng(seed,'time');kr=rng(seed,'K');lr=rng(seed,'location')
            words=[w['site_ids'] for w in scope['payload_words'] if field=='mixed' or w['word_id'].startswith(field+':')]
            sizes=np.array([len(w) for w in words]);total=int(sum(sizes));ends=np.cumsum(sizes)
            arrivals=[]
            if mode=='single':arrivals=[float(tr.uniform(0,20000))]
            elif mode=='repeat':
                t=0.
                while True:
                    t+=float(tr.exponential(1/c['cpp_repeat_rate_per_conditional']))
                    if t>=c['cpp_horizon_conditional']:break
                    arrivals.append(t)
            events=[]
            for t in arrivals:
                k=1 if mode=='single' or int(kr.integers(0,214))<205 else 2
                word=words[int(np.searchsorted(ends,int(lr.integers(0,total)),side='right'))]
                anchor=int(lr.integers(0,len(word)-k+1));events.append((t,word[anchor:anchor+k]))
            schedule=out/f'{name}.{mode}.{field}.n{n}.events.tsv'
            schedule.write_text(''.join(f'{t:.17g} '+ ';'.join(map(str,ids))+'\n' for t,ids in events))
            for label,scheme,k in variants:
                prefix=out/f'{name}.{mode}.{field}.n{n}.{label}'
                command=[str(ROOT/'build/periodic_scheduled'),str(ROOT/file['path']),str(c['cpp_anchor_conditional']),str(c['cpp_horizon_conditional']),scheme,str(schedule),mode,str(prefix),str(k)]
                tasks.append(dict(workload=name,mode=mode,field=field,trial=n,seed=seed,variant=label,k=k,command=command,output=str(prefix.relative_to(ROOT)),schedule_sha256=sha(schedule),input_sha256=file['sha256'],rng_namespaces={role:descriptor(seed,role) for role in ['time','K','location']}))
    assert len(tasks)==c['cpp_pilot_total_runs']
    report_path=ROOT/'reports/PERIODIC_CPP_DESIGN.json';results=[];started=time.perf_counter()
    def run(t):
        start=time.perf_counter();log=ROOT/(t['output']+'.log')
        with log.open('w') as f:
            try:p=subprocess.run(t['command'],cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=120)
            except subprocess.TimeoutExpired:return dict(t,status='FAIL_TIMEOUT')
        if p.returncode:return dict(t,status='FAIL_EXECUTION',exit_code=p.returncode)
        path=ROOT/(t['output']+'.csv')
        with path.open() as f:rows=list(csv.DictReader(f))
        assert len(rows)==1 and rows[0]['status']=='PASS'
        return dict(t,status='PASS',metrics=rows[0],CSV_sha256=sha(path),wall_seconds=time.perf_counter()-start)
    def persist(status):report_path.write_text(json.dumps(dict(status=status,config_sha256=sha(CONFIG),binary_sha256=sha(ROOT/'build/periodic_scheduled'),planned_runs=len(tasks),completed_runs=len(results),tasks=results,wall_seconds=time.perf_counter()-started),indent=2)+'\n')
    persist('RUNNING')
    # First two runs are a concrete runtime/health gate before wider dispatch.
    for t in tasks[:2]:
        r=run(t);results.append(r);persist('RUNNING');assert r['status']=='PASS'
    with concurrent.futures.ThreadPoolExecutor(max_workers=c['workers_cpp']) as pool:
        for r in pool.map(run,tasks[2:]):results.append(r);persist('RUNNING')
    assert all(r['status']=='PASS' for r in results);persist('PASS_FIXED_CPP_DESIGN_PILOT')
    scores={}
    for k in c['candidate_intervals']:
        rows=[r for r in results if r['k']==k]
        means=[]
        for name in c['cpp_design_workloads']:
            for mode in ['single','repeat']:
                values=[c['selection_proxy_cycles_per_extra_miss']*int(r['metrics']['net'])+c['selection_proxy_cycles_per_check']*int(r['metrics']['checks']) for r in rows if r['workload']==name and r['mode']==mode]
                means.append(float(np.mean(values)))
        scores[k]=float(np.mean(means))
    selected=min(c['candidate_intervals'],key=lambda k:(scores[k],k))
    selection={'status':'FROZEN_EXPLORATORY_CPP_PROXY_SELECTION_BEFORE_NEW_CPU_OUTCOMES','selected_interval':selected,'candidate_proxy_scores':scores,'rule':c['selection_rule'],'CPP_design_sha256':sha(report_path),'config_sha256':sha(CONFIG),'design_seed_base':c['cpp_design_seed_base'],'eval_repeat_seed_base':c['cpu_eval_repeat_seed_base'],'eval_single_seed_base':c['cpu_eval_single_seed_base'],'same_scope_sha256':c['scope_sha256'],'selection_uncertainty':'small design pilot; assumed20cycles/miss and1/check, not measured CPU optimization; final CPU evaluation does not retune k'}
    (ROOT/'sources/periodic_policy_selection.lock.json').write_text(json.dumps(selection,indent=2)+'\n')
    print(json.dumps({'status':'PASS_CPP_PILOT84_SELECTION_FROZEN','selected_interval':selected,'scores':scores}))

if __name__=='__main__':main()
