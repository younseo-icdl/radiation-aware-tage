#!/usr/bin/env python3
"""Detection-time ordering stress: count/timing/marks kept distinct from SEU physics."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import subprocess
import time
from pathlib import Path
import numpy as np
from rng_namespace import rng, descriptor
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'configs/flying_timing.lock.json'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def readcsv(p):
    with p.open() as f:return list(csv.DictReader(f))
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['pilot','main'],required=True);a=parser.parse_args()
    c=json.loads(CONFIG.read_text());sources={policy:[json.loads(s) for s in (ROOT/f'data/derived/flying_replay_{policy}.jsonl').read_text().splitlines()] for policy in c['duplicate_policies']}
    assert len(sources['collapse'])==2055 and len(sources['preserve'])==2129
    scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text());assert scope['scope_id']==c['scope_id']
    words=scope['payload_words'];ends=np.cumsum([w['payload_bits'] for w in words]);H=c['horizon_conditional_branches']
    windows={w['workload']:ROOT/w['split_files']['holdout']['path'] for w in json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())['workloads']}
    report_path=ROOT/('reports/FLYING_TIMING_'+a.phase.upper()+'.json');out=ROOT/'reports/flying_timing'/a.phase;out.mkdir(parents=True,exist_ok=True)
    if a.phase=='main':
        gate=json.loads((ROOT/'reports/FLYING_TIMING_PILOT.json').read_text());assert gate['status']=='PASS_SMALL_DETECTION_TIMING_PILOT' and gate['config_sha256']==sha(CONFIG) and gate['binary_sha256']==sha(ROOT/'build/scheduled')
    jobs=[]
    for wi,name in enumerate(c['workloads'][:1] if a.phase=='pilot' else c['workloads']):
        for policy in c['duplicate_policies']:
            for timing in c['timing_models']:
                for profile in c['K_profiles']:
                    for trial in range(1 if a.phase=='pilot' else c['trials_per_workload_condition']):jobs.append((wi,name,policy,timing,profile,trial))
    assert len(jobs)*4==(c['pilot_trials'] if a.phase=='pilot' else c['main_trials'])
    results=[];start=time.perf_counter()
    def run(job):
        wi,name,policy,timing,profile,trial=job;seed=(c['pilot_seed_base'] if a.phase=='pilot' else c['seed_base'])+wi*1000000+trial
        data=sources[policy];raw=np.array([r['time_seconds'] for r in data]);span=float(raw[-1]-raw[0]);gaps=np.diff(raw);assert span>0 and min(gaps)>=0
        clock=rng(seed,'time');phase=int(clock.integers(0,c['anchor_phase_range']))
        if timing=='permuted_detection_gaps':times=np.r_[0,np.cumsum(clock.permutation(gaps))]
        elif timing=='conditional_Poisson_fixed_N':times=np.sort(clock.uniform(0,span,size=len(data)))
        else:times=raw-raw[0]
        # The maximum is H-1, leaving a complete inclusive final branch bin.
        coordinates=times/span*(H-1);assert np.all(np.diff(coordinates)>=0) and np.min(coordinates)>=0 and np.max(coordinates)<H
        weights=c['K_profiles'][profile];events=[]
        for source,coordinate in zip(data,coordinates):
            # Stable group/occurrence marks preserve occurrence0 across policies;
            # no source detection is labeled a physical particle or an MCU.
            krng=rng(seed,'K',int(source['source_group']),int(source['record_in_group']));location=rng(seed,'location',int(source['source_group']),int(source['record_in_group']))
            k=1 if int(krng.integers(0,weights['1']+weights['2']))<weights['1'] else 2
            word=int(np.searchsorted(ends,int(location.integers(0,346)),side='right'));ids=words[word]['site_ids'];first=int(location.integers(0,len(ids)-k+1))
            events.append((float(coordinate),ids[first:first+k]))
        key=f'{name}.{policy}.{timing}.{profile}.n{trial}';folder=out/key;folder.mkdir(exist_ok=True)
        schedule=folder/'events.timing';schedule.write_text(''.join(f'{t:.17g} '+ ';'.join(map(str,ids))+'\n' for t,ids in events))
        card={'workload':name,'duplicate_policy':policy,'timing_model':timing,'K_profile':profile,'trial':trial,'seed':seed,'anchor_phase':phase,
              'rng_namespace_version':2,'clock_namespace':descriptor(seed,'time'),'record_namespace_grammar':'SeedSequence[magic,v2,master_lo,master_hi,role,source_group,record_in_group]',
              'source_rows':len(data),'source_span_seconds':span,'source_zero_gaps':int(np.sum(gaps==0)),
              'branch_exposure_density_records_per_conditional':len(data)/H,'target_rate_per_second':None,
              'schedule_sha256':sha(schedule),'replay_source_sha256':sha(ROOT/f'data/derived/flying_replay_{policy}.jsonl'),
              'K_status':'SBU assumption' if profile=='SBU' else 'independent CHARM hypothesis, not Flying Laptop measured K',
              'joint_distribution_measured':False,'physical_event_identity_verified':False,'counts_are_not_MCU_multiplicity':True}
        (folder/'model_card.json').write_text(json.dumps(card,indent=2)+'\n')
        output=[]
        for scheme in c['schemes']:
            prefix=folder/scheme;command=[str(ROOT/'build/scheduled'),str(windows[name]),str(c['holdout_anchor_base']+phase),str(H),scheme,str(schedule),key,str(prefix)]
            clock_start=time.perf_counter()
            with Path(str(prefix)+'.log').open('w') as f:
                try:p=subprocess.run(command,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,timeout=c['per_task_timeout_seconds'])
                except subprocess.TimeoutExpired:output.append(dict(card,scheme=scheme,status='FAIL_TIMEOUT',command=command));continue
            status=dict(card,scheme=scheme,command=command,log=str(Path(str(prefix)+'.log').relative_to(ROOT)),wall_seconds=time.perf_counter()-clock_start)
            if p.returncode:output.append(dict(status,status='FAIL_EXECUTION',exit_code=p.returncode));continue
            try:
                rows=readcsv(Path(str(prefix)+'.csv'));assert len(rows)==1;r=rows[0]
                assert r['status']=='PASS' and int(r['event_count'])==len(events) and int(r['flip_count'])==sum(len(ids) for _,ids in events)
                assert int(r['post_branches'])==H and int(r['net'])==int(r['harm'])-int(r['help'])==int(r['faulty_misses'])-int(r['clean_misses'])
                assert math.isclose(float(r['delta_MPKI']),1000*int(r['net'])/int(r['instructions']),rel_tol=1e-12,abs_tol=1e-12)
                applied=readcsv(Path(str(prefix)+'.events.csv'));assert len(applied)==len(events)
                for e,(t,ids) in zip(applied,events):assert float(e['coordinate'])==t and list(map(int,e['site_ids'].split(';')))==ids
                status.update(status='PASS',metrics=r,CSV=str(Path(str(prefix)+'.csv').relative_to(ROOT)),CSV_sha256=sha(Path(str(prefix)+'.csv')),events_CSV_sha256=sha(Path(str(prefix)+'.events.csv')))
            except Exception as error:status.update(status='FAIL_VALIDATION',error=str(error))
            output.append(status)
        return output
    report_path.write_text(json.dumps({'status':'RUNNING','planned_trials':len(jobs)*4},indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=c['workers']) as pool:
        for batch in pool.map(run,jobs):
            results+=batch;print(json.dumps({'completed':len(results),'failed':sum(r['status']!='PASS' for r in results)}),flush=True)
    failures=[r for r in results if r['status']!='PASS']
    result={'status':'PASS_SMALL_DETECTION_TIMING_PILOT' if a.phase=='pilot' and not failures else 'PASS_FIXED_DETECTION_TIMING_STRESS' if not failures else 'FAIL_EXECUTION_OR_VALIDATION',
        'phase':a.phase,'planned_trials':len(jobs)*4,'successful_trials':len(results)-len(failures),'failures':failures,'tasks':results,
        'config_sha256':sha(CONFIG),'binary_sha256':sha(ROOT/'build/scheduled'),'wall_seconds':time.perf_counter()-start,
        'physical_rate_or_strike_grouping_identified':False,'source_stream_boundary':'detected timestamps; no source-to-target per-bit/second conversion; duplicates are not MCU',
        'matched_marks':'same K/location per source group/occurrence and seed across time models and occurrence0 across policies',
        'replay_contract':'same complete 100k conditional horizon in real disjoint HW1 holdout, no resets between events, original instruction denominator'}
    report_path.write_text(json.dumps(result,indent=2)+'\n')
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
