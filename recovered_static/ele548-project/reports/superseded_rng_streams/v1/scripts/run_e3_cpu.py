#!/usr/bin/env python3
"""Fixed representative O3 clean/FI/latency plans; external event clock persists."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import os
import subprocess
import time
from functools import lru_cache
from pathlib import Path
import numpy as np
from run_o3_public_baseline import stats
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'configs/e3.cpu.lock.json'
SCHEMES=['P0','P_ED','P_ECC','P_TMR']
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

@lru_cache(maxsize=16)
def populations(scheme,pop):
    scope=json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
    words=[(w['word_id'],w['site_ids']) for w in scope['payload_words']]
    if pop=='selected_payload':return words,346
    fields=[[] for _ in range(6)]
    with (ROOT/'sources/tage_fault_sites.jsonl').open() as f:
        for line in f:
            row=json.loads(line);field=row['field'];kind=['bimodal','ctr','tag','u','raw_path','folded'].index(field)
            fields[kind].append(int(row['site_id'].split(':',1)[1]))
    pools=[(str(i),v) for i,v in enumerate(fields)];total=65370
    if pop=='storage_scaled_full':
        manifest=json.loads((ROOT/f'reports/e3_integration/gate/clean_{scheme}/logical_manifest.json').read_text())
        extras={}
        for s in manifest['additional_sites']:extras.setdefault((s['structure'],s['replica'],s['word']),[]).append(s['id'])
        pools += [(str(k),v) for k,v in extras.items()];total=manifest['total_bits']
    assert sum(len(v) for _,v in pools)==total
    return pools,total

def make_schedule(c,t,clean_end,outdir):
    seed=t['seed'];timing=np.random.Generator(np.random.PCG64(seed));krng=np.random.Generator(np.random.PCG64(seed+1));location=np.random.Generator(np.random.PCG64(seed+2))
    if t['mode']=='single':
        pools=[(name,ids) for name,ids in populations(t['scheme'],'selected_payload')[0] if name.startswith(t['field']+':')]
        total=sum(len(ids) for _,ids in pools);tick=int(timing.integers(int(.2*clean_end),int(.8*clean_end)))
        arrivals=[tick];rate=None;profile={'1':1,'2':0}
    else:
        pools,total=populations(t['scheme'],t['population']);profile=c['K_profiles'][t['profile']]
        mean_k=(profile['1']+2*profile['2'])/(profile['1']+profile['2']);rate=t['rate']
        if t['normalization']=='equal_expected_flip':rate/=mean_k
        if t['population']=='storage_scaled_full':rate*=total/65370
        arrivals=[];coordinate=.2*clean_end/500;limit=4*clean_end/500
        if t['mode']!='zero':
            while True:
                coordinate+=float(timing.exponential(1/rate))
                if coordinate>=limit:break
                arrivals.append(math.ceil(coordinate*500))
                if len(arrivals)>20000:raise RuntimeError('CPU schedule safety budget exceeded')
    sizes=np.array([len(ids) for _,ids in pools]);ends=np.cumsum(sizes);events=[]
    for tick in arrivals:
        p=int(np.searchsorted(ends,int(location.integers(0,total)),side='right'));pool=pools[p][1]
        k=1 if int(krng.integers(0,profile['1']+profile['2']))<profile['1'] else 2
        if k<=len(pool):
            first=int(location.integers(0,len(pool)-k+1));ids=pool[first:first+k]
        else:
            first=pool[0];second=int(location.integers(0,total-1));second+=second>=first;ids=[first,second]
        assert len(ids)==len(set(ids))==k
        events.append((tick,ids))
    path=outdir/'schedule.ticks';path.write_text(''.join(str(tick)+' '+ ';'.join(map(str,ids))+'\n' for tick,ids in events))
    mean_k=(profile['1']+2*profile['2'])/(profile['1']+profile['2'])
    card={'generator':'NumPy PCG64, independent time/K/location streams','time_seed':seed,'K_seed':seed+1,'location_seed':seed+2,
          'population':t['population'],'logical_exposed_bits':total,'base_rate_per_cycle':t['rate'],'actual_event_rate_per_cycle':rate,
          'expected_flip_rate_per_cycle':rate*mean_k if rate is not None else None,'start_tick':int(.2*clean_end),'model_stop_tick':4*clean_end,
          'scheduled_events':len(events),'scheduled_flips':sum(len(ids) for _,ids in events),'physical_mapping':None,'rate_status':c['rate_status'],
          'input_schedule_sha256':sha(path),'single_event_time':'uniform integer tick in [0.2,0.8) pristine duration' if t['mode']=='single' else None}
    (outdir/'schedule.json').write_text(json.dumps(card,indent=2)+'\n')
    return path,events,card

def task(program,scheme,mode='zero',field='mixed',profile='M0',pop='selected_payload',rate=0,normalization='equal_event',trial=0,seed=0,check=0,repair=0):
    key=f'{program}.{scheme}.{mode}.{field}.{profile}.{pop}.{normalization}.r{rate:.10g}.n{trial}.C{check}.R{repair}'
    return dict(program=program,scheme=scheme,mode=mode,field=field,profile=profile,population=pop,rate=rate,normalization=normalization,trial=trial,seed=seed,check=check,repair=repair,label=key)

def plan(c,phase):
    jobs=[];seed=c['pilot_seed_base'] if phase=='pilot' else c['main_seed_base']
    if phase in ['pilot','main']:
        for pi,program in enumerate(c['programs']):
            for scheme in SCHEMES:jobs.append(task(program,scheme,seed=seed+pi*1000000))
            if phase=='pilot' and program not in c['pilot_programs']:continue
            n=1 if phase=='pilot' else c['single_trials_per_program_field']
            for fi,field in enumerate(c['single_fields']):
                for trial in range(n):
                    for scheme in SCHEMES:jobs.append(task(program,scheme,'single',field,trial=trial,seed=seed+pi*1000000+fi*10000+trial))
            for profile in c['K_profiles']:
                normalizations=['equal_event'] if phase=='pilot' or profile=='M0' else ['equal_event','equal_expected_flip']
                for normalization in normalizations:
                    for pop in (['selected_payload'] if phase=='pilot' else c['repeat_populations']):
                        for rate in ([1e-6] if phase=='pilot' else c['base_event_rates_per_CPU_cycle']):
                            for trial in range(1 if phase=='pilot' else c['repeat_trials_per_program_condition']):
                                for scheme in SCHEMES:jobs.append(task(program,scheme,'repeat',profile=profile,pop=pop,rate=rate,normalization=normalization,trial=trial,seed=seed+pi*1000000+60000+trial))
    else:
        seed=c['latency_seed_base']
        for pi,program in enumerate(c['programs']):
            for check in c['latency_sensitivity']['check_cycles']:
                for scheme in SCHEMES[1:]:jobs.append(task(program,scheme,check=check,repair=4,seed=seed+pi*1000000))
            for trial in range(c['latency_sensitivity']['representative_repeat_trials']):
                s=seed+pi*1000000+60000+trial
                for scheme in SCHEMES:jobs.append(task(program,scheme,'repeat',profile='M1_CHARM_6T',rate=1e-6,trial=trial,seed=s))
                for check in c['latency_sensitivity']['check_cycles']:
                    for repair in c['latency_sensitivity']['repair_cycles']:
                        for scheme in SCHEMES[1:]:jobs.append(task(program,scheme,'repeat',profile='M1_CHARM_6T',rate=1e-6,trial=trial,seed=s,check=check,repair=repair))
    expected=c['pilot_total_runs'] if phase=='pilot' else c['main_ideal_runs'] if phase=='main' else c['latency_required_runs']
    assert len(jobs)==expected,(len(jobs),expected);assert len({t['label'] for t in jobs})==len(jobs)
    return jobs

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['pilot','main','latency','plan'],required=True);a=parser.parse_args()
    c=json.loads(CONFIG.read_text());native=json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text());pristine=json.loads((ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json').read_text())
    assert pristine['status']=='PASS_THREE_PRISTINE_O3_CLEAN_BASELINES'
    gate=json.loads((ROOT/'reports/E3_INTEGRATION_GATE.json').read_text());assert gate['status']=='PASS_REAL_O3_LOGICAL_INJECTION_SPECULATION_AND_RESPONSE_HOLD_GATE'
    binary=ROOT/'third_party/gem5-e3/build/X86_STAGE0/gem5.opt';assert sha(binary)==gate['binary_sha256']
    binary_sha256=sha(binary)
    assert sha(ROOT/'sources/protection_scope.lock.json')==c['scope_sha256']
    if a.phase=='plan':
        print(json.dumps({p:len(plan(c,p)) for p in ['pilot','main','latency']},indent=2));return
    if a.phase!='pilot':
        old=json.loads((ROOT/'reports/E3_CPU_PILOT.json').read_text());assert old['status']=='PASS_REPRESENTATIVE_CPU_PILOT' and old['binary_sha256']==sha(binary) and old['config_sha256']==sha(CONFIG)
    byname={x['name']:x for x in native['programs']};base={x['program']:x for x in pristine['programs']}
    env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    out=ROOT/'reports/e3_cpu'/a.phase;out.mkdir(parents=True,exist_ok=True)
    jobs=plan(c,a.phase);workers=c['workers_pilot'] if a.phase=='pilot' else c['workers_main']
    report_path=ROOT/('reports/E3_CPU_'+a.phase.upper()+'.json')
    results=[];start=time.perf_counter()
    def persist():
        report={'status':'RUNNING','phase':a.phase,'planned_runs':len(jobs),'completed_runs':len(results),'tasks':results,'binary_sha256':binary_sha256,'config_sha256':sha(CONFIG),'workers':workers}
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    persist()
    def run(t):
        item=byname[t['program']];baseline=base[t['program']];directory=out/t['label'];directory.mkdir(exist_ok=True)
        assert sha(ROOT/item['binary'])==item['binary_sha256'] and sha(ROOT/item['input'])==item['input_sha256']
        clean_end=baseline['cycles']*500;path,events,card=make_schedule(c,t,clean_end,directory)
        command=[str(binary),'--outdir='+str(directory),str(ROOT/'gem5/o3_seu.py'),'--binary',str(ROOT/item['binary']),'--input',str(ROOT/item['input']),
            '--scheme',t['scheme'],'--schedule',str(path),'--check-cycles',str(t['check']),'--repair-cycles',str(t['repair']),'--max-ticks',str(4*clean_end)]
        record=dict(t,command=command,output=str(directory.relative_to(ROOT)),schedule_card=card,log=str((directory/'gem5.log').relative_to(ROOT)))
        clock=time.perf_counter()
        with (directory/'gem5.log').open('w') as f:
            try:p=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=c['per_run_wall_timeout_seconds'])
            except subprocess.TimeoutExpired:return dict(record,status='FAIL_WALL_TIMEOUT',wall_seconds=time.perf_counter()-clock)
        record.update(exit_code=p.returncode,wall_seconds=time.perf_counter()-clock)
        if p.returncode:
            log=(directory/'gem5.log').read_text(errors='replace');return dict(record,status='FAIL_MODEL_TIME_LIMIT' if 'simulate() limit reached' in log else 'FAIL_EXECUTION')
        try:
            assert sha(directory/'program.stdout')==item['native_stdout_sha256'] and not (directory/'program.stderr').read_bytes()
            log=(directory/'gem5.log').read_text();assert 'Exit cause: exiting with last active thread context code: 0' in log
            if 'ignoring syscall' in log.lower() or 'unimplemented syscall' in log.lower():return dict(record,status='FAIL_UNSUPPORTED_SYSCALL')
            s=stats(directory/'stats.txt');seu=json.loads((directory/'seu.json').read_text());ni=int(s['system.cpu.commitStats0.numInsts']);cy=int(s['system.cpu.numCycles'])
            assert ni==baseline['committed_instructions']==int(s['simInsts'])
            expected=sum(tick<=seu['end_tick'] for tick,_ in events);assert seu['applied_events']==expected
            assert seu['applied_flips']==sum(len(ids) for tick,ids in events if tick<=seu['end_tick'])
            with (directory/'events.csv').open() as f:
                applied=list(csv.DictReader(f));assert len(applied)==expected
            for rr,(tick,ids) in zip(applied,events):assert int(rr['tick'])==tick and list(map(int,rr['site_ids'].split(';')))==ids and rr['XOR_verified']=='1'
            if t['mode']=='zero' and t['check']==0:assert cy==baseline['cycles'] and seu['detected']==0
            if t['mode']=='single' and t['scheme'] in ['P_ECC','P_TMR'] and t['check']==0:assert cy==baseline['cycles'] and seu['corrected']>=1
            mis=s['system.cpu.branchPred.mispredicted_0::DirectCond']+s['system.cpu.branchPred.mispredicted_0::IndirectCond']
            record.update(status='PASS',cycles=cy,committed_instructions=ni,IPC=s['system.cpu.ipc'],IPC_from_counts=ni/cy,conditional_mispredictions=int(mis),conditional_MPKI=1000*mis/ni,
                delta_cycles_from_pristine=cy-baseline['cycles'],slowdown_from_pristine=cy/baseline['cycles']-1,delta_IPC_from_pristine=s['system.cpu.ipc']-baseline['IPC'],
                seu=seu,stats_sha256=sha(directory/'stats.txt'),seu_sha256=sha(directory/'seu.json'),stdout_sha256=sha(directory/'program.stdout'),config_sha256=sha(directory/'config.json'),
                fetch_stalls={k:v for k,v in s.items() if k.startswith('system.cpu.fetch.') and any(w in k.lower() for w in ['stall','squash','icachewait'])})
        except Exception as error:record.update(status='FAIL_VALIDATION',error=str(error))
        return record
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(run,t):t for t in jobs}
        for f in concurrent.futures.as_completed(futures):
            r=f.result();results.append(r);persist()
            print(json.dumps({k:r.get(k) for k in ['program','scheme','mode','status','cycles','wall_seconds','label']},ensure_ascii=False),flush=True)
    failures=[r for r in results if r['status']!='PASS'];report=json.loads(report_path.read_text());elapsed=time.perf_counter()-start
    report.update(status='PASS_REPRESENTATIVE_CPU_PILOT' if a.phase=='pilot' and not failures else 'PASS_FIXED_CPU_'+a.phase.upper() if not failures else 'FAIL_EXECUTION_OR_VALIDATION',
        failures=failures,wall_seconds=elapsed,successful_runs=len(results)-len(failures),native_manifest_sha256=sha(ROOT/'reports/E3_PUBLIC_WORKLOADS.json'),
        pristine_baseline_sha256=sha(ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json'),source_lock_sha256=sha(ROOT/'sources/gem5_e3_source.lock.json'),gate_sha256=sha(ROOT/'reports/E3_INTEGRATION_GATE.json'),
        planned_main_total_runs=c['total_main_runs'],projected_main_serial_seconds=sum(r['wall_seconds'] for r in results)/len(results)*c['total_main_runs'],
        runtime_projection_boundary='fixed pilot tasks; host concurrency/contention and program/latency-dependent duration matter; not CPU performance prediction')
    report_path.write_text(json.dumps(report,indent=2)+'\n')
    if failures:raise SystemExit(1)
if __name__=='__main__':main()
