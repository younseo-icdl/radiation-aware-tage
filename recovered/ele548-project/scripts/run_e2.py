#!/usr/bin/env python3
"""Correctness/<=100-trial preflight, then locked E2 holdout evaluation."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import statistics
import subprocess
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/e2.holdout.lock.json'

def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def rows(p):
    with p.open() as f: return list(csv.DictReader(f))

def qualify(c):
    assert sha(ROOT/'sources/protection_scope.lock.json') == c['scope_sha256']
    frozen=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
    expected={w['word_id']:set(w['site_ids']) for w in frozen['payload_words']}
    counts={};extra={};selected={}
    for r in rows(ROOT/'sources/e2_stored_sites.csv'):
        scheme=r['scheme'];counts[scheme]=counts.get(scheme,0)+1
        if r['selected_payload']=='1':selected.setdefault(scheme,{}).setdefault(r['word_id'],set()).add(int(r['site_id']))
        if int(r['site_id'])>=65370:extra.setdefault(scheme,[]).append(r)
    assert counts=={'P0':65370,'P_ED':65433,'P_ECC':65531,'P_TMR':66062},counts
    assert all(selected[s]==expected for s in c['schemes'])
    for s in c['schemes']:assert [int(r['site_id']) for r in extra.get(s,[])]==list(range(65370,counts[s]))
    record={'status':'PASS_ACTUAL_STORED_BIT_ENUMERATION','scope_id':c['scope_id'],'base_manifest':'sources/tage_fault_sites.jsonl',
            'generated_full_manifest':'sources/e2_stored_sites.csv','full_manifest_sha256':sha(ROOT/'sources/e2_stored_sites.csv'),
            'total_bits':counts,'extra_counts':{s:dict(Counter(r['structure'] for r in extra.get(s,[]))) for s in c['schemes']},
            'additional_sites':extra,'payload_words':frozen['payload_words'],'statistics_and_simulator_slack_exposed':False,
            'same_scope_match':'PASS_ALL_FOUR_346_BITS_23_WORDS','physical_mapping':None,
            'functional_boundary':'non-spec behavioral replay; epoch exposed but functionally inert here; CPU in-flight state and shared combinational SET excluded; E3 must revisit rollback metadata'}
    (ROOT/'sources/e2_protection_logical_manifest.json').write_text(json.dumps(record,indent=2)+'\n')
    manifest=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())
    assert manifest['status']=='PASS_COMPLETE_DISJOINT_REAL_WINDOWS'
    byname={x['workload']:x for x in manifest['workloads']};inputs=[]
    for i,name in enumerate(c['workloads']):
        item=byname[name]['split_files']['holdout'];p=ROOT/item['path'];assert sha(p)==item['sha256']
        assert item['original_conditional_base']+c['holdout_local_anchor']==c['holdout_original_anchor']
        inputs.append((i,name,p))
    assert 'PASS' in (ROOT/'reports/e2_correctness.log').read_text()
    return inputs

def task(c,item,mode,model,n,seed,pop='selected_payload',field=6,rate=0,label=None):
    return {'item':item,'mode':mode,'model':model,'n':n,'seed':seed,'pop':pop,'field':field,'rate':rate,
            'label':label or f'{item[1]}.{mode}.{model}.{pop}.f{field}.r{rate:.12g}'}

def run_task(c,t,outdir):
    i,name,path=t['item'];key=t['label'];prefix=outdir/key;profile=c['K_profiles'].get(t['model'].split('__')[0],{'1':1,'2':0})
    command=[str(ROOT/'build/e2_campaign'),str(path),name,str(i),str(c['holdout_local_anchor']),str(c['single_injection_prefix']),
             str(c['horizon_conditional_branches']),str(t['n']),str(profile['1']),str(profile['2']),t['model'],t['mode'],t['pop'],
             str(t['field']),str(t['rate']),str(t['seed']),str(prefix)]
    status={'status':'RUNNING','command':command,'output':str(prefix.with_suffix('.csv').relative_to(ROOT))}
    # A rate contains a decimal dot, so append extensions (do not replace suffix).
    summary=Path(str(prefix)+'.csv');events=Path(str(prefix)+'.events.csv');log=Path(str(prefix)+'.log')
    status.update(output=str(summary.relative_to(ROOT)),event_CSV=str(events.relative_to(ROOT)),log=str(log.relative_to(ROOT)))
    start=time.perf_counter()
    with log.open('w') as f:
        try:p=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=c['per_task_timeout_seconds'])
        except subprocess.TimeoutExpired:return dict(status,status='FAIL_TIMEOUT',wall_seconds=time.perf_counter()-start)
    if p.returncode:return dict(status,status='FAIL_EXECUTION',exit_code=p.returncode,wall_seconds=time.perf_counter()-start)
    try:
        result=rows(summary);assert len(result)==t['n']*4
        for r in result:
            assert r['status']=='PASS' and int(r['post_branches'])==c['horizon_conditional_branches']
            assert int(r['net'])==int(r['harm'])-int(r['help'])==int(r['faulty_misses'])-int(r['clean_misses'])
            assert math.isclose(float(r['delta_MPKI']),1000*int(r['net'])/int(r['instructions']),rel_tol=1e-12,abs_tol=1e-12)
            if t['model']=='ZERO':assert int(r['net'])==int(r['end_differing_base_bits'])==int(r['detected'])==0 and r['end_controls_equal']=='1'
        pertrial=Counter();flips=Counter();signatures={}
        with events.open() as f:
            for e in csv.DictReader(f):
                ids=[int(x) for x in e['event_site_ids'].split(';')];assert len(ids)==len(set(ids))==int(e['multiplicity'])
                key=(e['scheme'],e['trial']);pertrial[key]+=1;flips[key]+=len(ids)
                signatures.setdefault(key,[]).append((e['arrival_conditional_coordinate'],e['event_site_ids']))
        for r in result:
            key=(r['scheme'],r['trial']);assert int(r['event_count'])==pertrial[key] and int(r['flip_count'])==flips[key]
            if t['pop']!='storage_scaled_full':assert signatures.get(key,[])==signatures.get(('P0',r['trial']),[])
        status.update(status='PASS',successful_trials=len(result),CSV_sha256=sha(summary),event_CSV_sha256=sha(events),
                      wall_seconds=time.perf_counter()-start,mean_trial_seconds=statistics.mean(float(r['wall_seconds']) for r in result),
                      peak_RSS_KiB=max(int(r['peak_rss_kib']) for r in result))
    except Exception as e:status.update(status='FAIL_VALIDATION',error=str(e))
    return status

def execute(c,tasks,outdir):
    output=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=c['workers']) as pool:
        future_map={pool.submit(run_task,c,t,outdir):t for t in tasks}
        for f in concurrent.futures.as_completed(future_map):
            result=f.result();output.append(result)
            print(json.dumps({k:result.get(k) for k in ['status','output','successful_trials','wall_seconds']},ensure_ascii=False),flush=True)
    return output

def preflight(c,inputs,outdir):
    seed=c['preflight_seed_base'];tasks=[]
    for item in inputs[:2]:
        for field in c['single_fields']:tasks.append(task(c,item,'single','M0',5,seed,field=field))
    tasks += [task(c,inputs[0],'repeat','ZERO',1,seed,label='zero4'),task(c,inputs[0],'repeat','M0',1,seed,rate=.001,label='repeat4'),
              task(c,inputs[0],'repeat','M0',1,seed,rate=.001,label='determinism4')]
    start=time.perf_counter();result=execute(c,tasks,outdir);failures=[r for r in result if r['status']!='PASS']
    ignored={'wall_seconds','peak_rss_kib'}
    if not failures:
        a=rows(outdir/'repeat4.csv');b=rows(outdir/'determinism4.csv')
        assert [{k:v for k,v in r.items() if k not in ignored} for r in a]==[{k:v for k,v in r.items() if k not in ignored} for r in b]
        assert sha(outdir/'repeat4.events.csv')==sha(outdir/'determinism4.events.csv')
    trials=sum(r.get('successful_trials',0) for r in result);assert trials<=c['preflight_max_predictor_trials']
    cost=statistics.mean(r['mean_trial_seconds'] for r in result if r['status']=='PASS')
    report={'status':'PASS_CORRECTNESS_AND_SMALL_PILOT' if not failures else 'FAIL_PREFLIGHT','tasks':result,'failures':failures,
            'config_sha256':sha(CONFIG),'binary_sha256':sha(ROOT/'build/e2_campaign'),'manifest_sha256':sha(ROOT/'sources/e2_protection_logical_manifest.json'),
            'predictor_trials':trials,'wall_seconds':time.perf_counter()-start,'mean_task_trial_seconds':cost,
            'projected_serial_trial_work_seconds':cost*(c['fixed_main_trials']+c['fixed_zero_trials']),
            'runtime_limit':'projection from two workloads; excludes per-task warmup/gold preparation and task startup; workload and detection cadence affect runtime',
            'determinism':'PASS_MATCHED_OUTPUTS_AND_FULL_EVENT_SCHEDULE' if not failures else 'NOT_CONFIRMED','CPU_cycles_IPC_measured':False}
    (ROOT/'reports/E2_PREFLIGHT.json').write_text(json.dumps(report,indent=2)+'\n')
    if failures:raise SystemExit(1)

def main_campaign(c,inputs,outdir):
    gate=json.loads((ROOT/'reports/E2_PREFLIGHT.json').read_text());assert gate['status']=='PASS_CORRECTNESS_AND_SMALL_PILOT'
    assert gate['config_sha256']==sha(CONFIG) and gate['binary_sha256']==sha(ROOT/'build/e2_campaign')
    assert gate['manifest_sha256']==sha(ROOT/'sources/e2_protection_logical_manifest.json')
    tasks=[]
    for item in inputs:
        tasks.append(task(c,item,'repeat','ZERO',1,c['repeat_seed_base'],label=item[1]+'.zero'))
        for field in c['single_fields']:tasks.append(task(c,item,'single','M0',c['single_trials_per_workload_selected_field'],c['single_seed_base'],field=field))
        for model,p in c['K_profiles'].items():
            mean_k=(p['1']+2*p['2'])/(p['1']+p['2'])
            for normalization in (['equal_event'] if model=='M0' else ['equal_event','equal_expected_flip']):
                for rate in c['base_event_rates_per_conditional']:
                    for pop in c['repeat_populations']:
                        tasks.append(task(c,item,'repeat',model+'__'+normalization,c['repeat_trials_per_workload_condition'],c['repeat_seed_base'],pop=pop,
                                          rate=rate if normalization=='equal_event' else rate/mean_k))
    assert sum(t['n']*4 for t in tasks)==c['fixed_main_trials']+c['fixed_zero_trials']
    report_path=ROOT/'reports/E2_CAMPAIGN.json';report_path.write_text(json.dumps({'status':'RUNNING','planned_trials':c['fixed_main_trials']+c['fixed_zero_trials']},indent=2)+'\n')
    start=time.perf_counter();result=execute(c,tasks,outdir);failures=[r for r in result if r['status']!='PASS'];allrows=[]
    for r in result:
        if r['status']=='PASS':allrows.extend(rows(ROOT/r['output']))
    aggregate=outdir/'trials.csv'
    if allrows:
        with aggregate.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(allrows[0]),lineterminator='\n');writer.writeheader();writer.writerows(allrows)
    report={'status':'PASS_FIXED_HOLDOUT_E2' if not failures else 'FAIL_EXECUTION_OR_VALIDATION','planned_trials':c['fixed_main_trials']+c['fixed_zero_trials'],
            'successful_trials':len(allrows),'tasks':result,'failures':failures,'config_sha256':sha(CONFIG),'binary_sha256':sha(ROOT/'build/e2_campaign'),
            'manifest_sha256':sha(ROOT/'sources/e2_protection_logical_manifest.json'),'input_manifest_sha256':sha(ROOT/'reports/E1_WORKLOAD_WINDOWS.json'),
            'trial_CSV':str(aggregate.relative_to(ROOT)),'trial_CSV_sha256':sha(aggregate) if allrows else None,'wall_seconds':time.perf_counter()-start,
            'peak_RSS_KiB':max((int(r['peak_rss_kib']) for r in allrows),default=None),'CPU_cycles_IPC_measured':False,'holdout_performance_evaluated':True,
            'scope_frozen_sha256':c['scope_sha256'],'budget':'fixed 960 single +7200 repeat +24 zero trials; no outcome-dependent extension or stopping'}
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    if failures:raise SystemExit(1)

def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['preflight','main','qualify'],required=True);a=p.parse_args()
    c=json.loads(CONFIG.read_text());inputs=qualify(c)
    if a.phase=='qualify':print('PASS same S*, actual added storage, all holdout input hashes');return
    outdir=ROOT/'reports/e2'/a.phase;outdir.mkdir(parents=True,exist_ok=True)
    preflight(c,inputs,outdir) if a.phase=='preflight' else main_campaign(c,inputs,outdir)

if __name__=='__main__':main()
