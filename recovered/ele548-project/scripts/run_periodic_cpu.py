#!/usr/bin/env python3
"""42 new evaluations; reuse exact matched, audited four-baseline schedules."""
import concurrent.futures
import csv
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from run_o3_public_baseline import stats
from summarize_e3_cpu import sha
ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/'configs/periodic_extension.lock.json'

def validate_reference(r,native):
    assert r['status']=='PASS'
    d=ROOT/r['output']
    for name,field in [('stats.txt','stats_sha256'),('seu.json','seu_sha256'),('config.json','config_sha256')]:assert sha(d/name)==r[field]
    assert sha(d/'program.stdout')==native['native_stdout_sha256']==r['stdout_sha256']
    st=stats(d/'stats.txt')
    assert int(st['system.cpu.numCycles'])==r['cycles'] and int(st['system.cpu.commitStats0.numInsts'])==r['committed_instructions']
    assert sha(d/'schedule.ticks')==r['schedule_card']['input_schedule_sha256']

def plan(c,selection,main,latency,native):
    k=selection['selected_interval'];jobs=[];refs=[]
    for pi,program in enumerate(c['cpu_programs']):
        own=[]
        for scheme in c['required_baselines']:
            check,repair=(0,0) if scheme=='P0' else (1,4)
            clean_source=main if scheme=='P0' else latency
            clean=next(r for r in clean_source['tasks'] if r['program']==program and r['scheme']==scheme and r['mode']=='zero' and r['check']==check and r['repair']==repair)
            validate_reference(clean,native[program]);refs.append(dict(clean,reference_role='clean'))
            for n in range(c['cpu_repeated_eval_trials_per_program']):
                r=next(r for r in latency['tasks'] if r['program']==program and r['scheme']==scheme and r['mode']=='repeat' and r['profile']=='M1_CHARM_6T' and r['population']=='selected_payload' and r['normalization']=='equal_event' and r['rate']==c['cpu_event_rate_per_cycle'] and r['trial']==n and r['check']==check and r['repair']==repair)
                validate_reference(r,native[program]);refs.append(dict(r,reference_role='repeat'))
                if scheme=='P0':own.append(dict(program=program,mode='repeat',field='mixed',trial=n,seed=r['seed'],reference_output=r['output'],reference_schedule_sha256=r['schedule_card']['input_schedule_sha256'],interval=k))
        for field in c['single_fields']:
            for n in range(c['cpu_single_eval_trials_per_field']):
                r=next(r for r in main['tasks'] if r['program']==program and r['scheme']=='P0' and r['mode']=='single' and r['field']==field and r['trial']==n)
                validate_reference(r,native[program]);refs.append(dict(r,reference_role='single_P0'))
                own.append(dict(program=program,mode='single',field=field,trial=n,seed=r['seed'],reference_output=r['output'],reference_schedule_sha256=r['schedule_card']['input_schedule_sha256'],interval=k))
        jobs.append(dict(program=program,mode='zero',field='mixed',trial=0,seed=c['cpu_eval_repeat_seed_base']+pi*1000000,reference_output=None,reference_schedule_sha256=None,interval=k))
        jobs+=own
    assert len(jobs)==c['cpu_new_runs']
    return jobs,refs

def main():
    c=json.loads(CONFIG.read_text());selection=json.loads((ROOT/'sources/periodic_policy_selection.lock.json').read_text())
    assert selection['config_sha256']==sha(CONFIG) and selection['CPP_design_sha256']==sha(ROOT/'reports/PERIODIC_CPP_DESIGN.json')
    gate=json.loads((ROOT/'reports/PERIODIC_CPU_GATE.json').read_text());assert gate['status']=='PASS_ISOLATED_PERIODIC_REAL_O3_GATE'
    binary=ROOT/'third_party/gem5-periodic/build/X86_STAGE0/gem5.opt';assert sha(binary)==gate['binary_sha256']
    base=json.loads((ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json').read_text());pristine={r['program']:r for r in base['programs']}
    native={r['name']:r for r in json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text())['programs']}
    main_ref=json.loads((ROOT/'reports/E3_CPU_MAIN.json').read_text());lat_ref=json.loads((ROOT/'reports/E3_CPU_LATENCY.json').read_text())
    for phase,report in [('MAIN',main_ref),('LATENCY',lat_ref)]:
        summary=json.loads((ROOT/f'reports/E3_CPU_{phase}_SUMMARY.json').read_text())
        assert summary['status']=='PASS_AUDITED_COMPLETE_CPU_PHASE' and summary['campaign_sha256']==sha(ROOT/f'reports/E3_CPU_{phase}.json')
    jobs,refs=plan(c,selection,main_ref,lat_ref,native)
    design_seeds={r['seed'] for r in json.loads((ROOT/'reports/PERIODIC_CPP_DESIGN.json').read_text())['tasks']}
    assert not design_seeds.intersection(r['seed'] for r in jobs)
    out=ROOT/'reports/periodic_extension/cpu_eval';out.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env['LD_LIBRARY_PATH']='/opt/miniconda3/lib'+(':'+env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
    result_path=ROOT/'reports/PERIODIC_CPU_EVAL.json';results=[];start=time.perf_counter()
    def persist(status):
        report=dict(status=status,config_sha256=sha(CONFIG),selection_sha256=sha(ROOT/'sources/periodic_policy_selection.lock.json'),source_lock_sha256=sha(ROOT/'sources/gem5_periodic_source.lock.json'),gate_sha256=sha(ROOT/'reports/PERIODIC_CPU_GATE.json'),binary_sha256=gate['binary_sha256'],baseline_campaign_hashes={f'reports/E3_CPU_{p}.json':sha(ROOT/f'reports/E3_CPU_{p}.json') for p in ['MAIN','LATENCY']},planned_runs=len(jobs),completed_runs=len(results),tasks=results,baseline_references=refs,wall_seconds=time.perf_counter()-start)
        tmp=result_path.with_suffix('.json.tmp');tmp.write_text(json.dumps(report,indent=2)+'\n');tmp.replace(result_path)
    def run(t):
        item=native[t['program']];clean=pristine[t['program']];label=f"{t['program']}.{t['mode']}.{t['field']}.n{t['trial']}.k{t['interval']}"
        d=out/label;d.mkdir(exist_ok=True);schedule=d/'schedule.ticks'
        if t['reference_output']:
            shutil.copyfile(ROOT/t['reference_output']/'schedule.ticks',schedule);assert sha(schedule)==t['reference_schedule_sha256']
        else:schedule.write_text('')
        assert sha(ROOT/item['binary'])==item['binary_sha256'] and sha(ROOT/item['input'])==item['input_sha256']
        command=[str(binary),'--outdir='+str(d),str(ROOT/'gem5/o3_periodic.py'),'--binary',str(ROOT/item['binary']),'--input',str(ROOT/item['input']),'--scheme','P_ED','--inspection-interval',str(t['interval']),'--schedule',str(schedule),'--check-cycles',str(c['cpu_check_cycles']),'--repair-cycles',str(c['cpu_repair_cycles']),'--max-ticks',str(clean['cycles']*500*4)]
        record=dict(t,label=label,scheme='P_PERIODIC_ED',check=c['cpu_check_cycles'],repair=c['cpu_repair_cycles'],command=command,output=str(d.relative_to(ROOT)),schedule_sha256=sha(schedule))
        clock=time.perf_counter()
        with (d/'gem5.log').open('w') as f:
            try:p=subprocess.run(command,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=c['per_run_wall_timeout_seconds'])
            except subprocess.TimeoutExpired:return dict(record,status='FAIL_WALL_TIMEOUT',wall_seconds=time.perf_counter()-clock)
        record.update(exit_code=p.returncode,wall_seconds=time.perf_counter()-clock)
        if p.returncode:return dict(record,status='FAIL_EXECUTION_OR_MODEL_STOP')
        try:
            assert sha(d/'program.stdout')==item['native_stdout_sha256'] and not (d/'program.stderr').read_bytes()
            log=(d/'gem5.log').read_text();assert 'Exit cause: exiting with last active thread context code: 0' in log
            assert 'ignoring syscall' not in log.lower() and 'unimplemented syscall' not in log.lower()
            st=stats(d/'stats.txt');seu=json.loads((d/'seu.json').read_text());manifest=json.loads((d/'logical_manifest.json').read_text())
            ni=int(st['system.cpu.commitStats0.numInsts']);cy=int(st['system.cpu.numCycles'])
            assert ni==clean['committed_instructions']==int(st['simInsts']) and cy>0
            assert seu['inspection_interval']==t['interval'] and manifest['total_bits']==65442
            events=[(int(line.split()[0]),list(map(int,line.split()[1].split(';')))) for line in schedule.read_text().splitlines()]
            expected=[e for e in events if e[0]<=seu['end_tick']]
            assert len(expected)==seu['applied_events'] and sum(len(ids) for _,ids in expected)==seu['applied_flips']
            with (d/'events.csv').open() as f:applied=list(csv.DictReader(f))
            assert len(applied)==len(expected)
            for rr,(tick,ids) in zip(applied,expected):
                assert int(rr['tick'])==tick and list(map(int,rr['site_ids'].split(';')))==ids and rr['XOR_verified']=='1'
            with (d/'events.csv.repairs.csv').open() as f:repairs=list(csv.DictReader(f))
            assert len(repairs)==seu['repair_batches']
            previous=0
            for rr in repairs:
                busy=max(previous,int(rr['tick']))+500*c['cpu_repair_cycles'];assert int(rr['repair_busy_until'])==busy;previous=busy
            assert sum(seu['repairs_by_origin'])==len(repairs)
            if t['mode']=='zero':assert seu['detected']==seu['applied_events']==0
            mis=st['system.cpu.branchPred.mispredicted_0::DirectCond']+st['system.cpu.branchPred.mispredicted_0::IndirectCond']
            record.update(status='PASS',cycles=cy,committed_instructions=ni,IPC=ni/cy,conditional_mispredictions=int(mis),conditional_MPKI=1000*mis/ni,seu=seu,stats_sha256=sha(d/'stats.txt'),seu_sha256=sha(d/'seu.json'),config_sha256=sha(d/'config.json'),stdout_sha256=sha(d/'program.stdout'),event_log_sha256=sha(d/'events.csv'),repair_log_sha256=sha(d/'events.csv.repairs.csv'),manifest_sha256=sha(d/'logical_manifest.json'),fetch_stalls={key:val for key,val in st.items() if key.startswith('system.cpu.fetch.') and any(s in key.lower() for s in ['stall','squash','icachewait'])})
        except Exception as e:record.update(status='FAIL_VALIDATION',error=str(e))
        return record
    persist('RUNNING')
    # Exactly two serial clean program runs prove runtime/answers/health.
    first=[r for r in jobs if r['mode']=='zero']
    for t in first:
        r=run(t);results.append(r);persist('RUNNING');print(json.dumps({k:r.get(k) for k in ['label','status','cycles','wall_seconds']}),flush=True)
        if r['status']!='PASS':raise SystemExit('clean engineering gate failed')
    with concurrent.futures.ThreadPoolExecutor(max_workers=c['workers_cpu']) as pool:
        for r in pool.map(run,[t for t in jobs if t['mode']!='zero']):
            results.append(r);persist('RUNNING');print(json.dumps({k:r.get(k) for k in ['label','status','cycles','wall_seconds']}),flush=True)
    persist('PASS_FIXED_PERIODIC_CPU_EVALUATION' if all(r['status']=='PASS' for r in results) else 'COMPLETE_WITH_RETAINED_FAILURES')
    print('completed',len(results),'failures',sum(r['status']!='PASS' for r in results),flush=True)
if __name__=='__main__':main()
