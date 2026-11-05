"""Frozen fresh-input/owner V9 chunk2; never dispatch from import.

Root freezes the actual conventional candidate after development. This runner
uses the existing producer and timeout-safe run_one, without changing chunk1.
"""
import argparse, concurrent.futures, datetime, json, re, shutil
from pathlib import Path
import native_v9_common as c
from native_v9_campaign import semantic_map
from rng_namespace import rng, descriptor

ROOT, OUT = c.ROOT, c.OUT
CONVENTIONAL = ['C_PAR_FREQUENT','C_PAR_PERIODIC','C_ECC','C_TMR']
PHASES = ['HOLDOUT_CLEAN','HOLDOUT_FAULT']
SOURCE_NAME = 'SOURCE_RAW130_CHARM_2000S'
POLICY = dict(status='DECLARED_BEFORE_CHUNK2_CPU',phase='HOLDOUT_FAULT',scenario_prefix='WHOLE_K1_REF_SCALE',row_status='FAIL_EXECUTION',exception_types=['bp::v9::MirrorUncorrectable','bp::QueueIntegrityError'],messages=['both SECDED copies DUE','valid SECDED copies disagree','valid source copies encode out-of-range head'],interpretation='Keep actual failed status/exit/raw and invalid pairs; decoder exception alone does not prove causal3plus. All SOURCE, normal, timeout, assertion, unsupported ISA/syscall and generic errors stop their phase.')

def put(path,data):
    assert not path.exists(),('IMMUTABLE_CHUNK2_EVIDENCE',str(path))
    c.write(path,data)

def checked_ref(value):
    path=ROOT/value['path'];assert path.is_file() and c.sha(path)==value['sha256'],('CHUNK2_REFERENCE_CHANGED',value)
    return path

def candidate():
    path=OUT/'configs/CONFIRMATION_CANDIDATE.lock.json';d=c.load(path)
    assert d['status']=='FROZEN_BEFORE_NEW_INPUT_AND_OWNERS'
    assert d['candidate_id']=='A_DIR' and d['conventional_id'] in CONVENTIONAL
    assert d['schemes']==['U',d['conventional_id'],'A_DIR']
    assert d['domain']=='WHOLE_AND_SOURCE'
    assert d['scales']==[10**15,10**16] and d['owners_per_program_scale']==2
    assert d.get('source_extra_schemes',[]) in [[],['C_ECC','C_TMR']]
    source=d['source_scenario']
    assert source==dict(name=SOURCE_NAME,event_rate_per_second=2000,K_counts={'1':205,'2':9},placement='uniform_valid_contiguous_raw130_logical_age')
    checked_ref(d['selection_evidence']);checked_ref(d['development_analysis'])
    selection=c.load(checked_ref(d['selection_evidence']))
    assert selection['selected_policy']==d['conventional_id'],'CONVENTIONAL_NOT_DEVELOPMENT_SELECTION'
    return d

def verify_bound():
    c.verify_sources();p=c.load(OUT/'configs/PRODUCER.lock.json')
    assert p['status']=='PASS_NATIVE_L0_CPU_GATE_BEFORE_DEVELOPMENT'
    assert c.sha(c.BINARY)==p['binary_sha256'] and c.sha(c.CONFIG)==p['config_sha256']
    refs=c.load(OUT/'configs/EXPERIMENT_REFERENCES.lock.json')
    for name,digest in refs['files'].items():assert c.sha(ROOT/name)==digest,('FROZEN_HELPER_CHANGED',name)
    return p

def markers():return list((OUT/'reports/run_starts').glob('*.json'))
def phase_markers():return [p for p in markers() if c.load(p).get('phase') in PHASES]

def check_budget(reserve=0):
    assert not list((OUT/'reports').rglob('*.timeout.json')),'UNRESOLVED_TIMEOUT_ACCOUNTING'
    assert 3009+len(markers())+reserve<=3200,'ORIGINAL_GLOBAL3200_CPU_CAP'
    assert len(phase_markers())+reserve<=120,'CHUNK2_CPU_CAP120'
    prior=[p for p in markers() if c.load(p).get('phase') not in PHASES]
    assert len(prior)<=120,'FIRST_CHUNK_CAP_UNCHANGED'
    used=c.used_seconds();disk=c.disk_gib()
    assert used<12*3600 and 65.39845555555556+used/3600<108,'ORIGINAL_CORE_HOUR_CAP'
    assert disk<8 and 20.54370880126953+disk<34,'ORIGINAL_DISK_CAP'
    assert shutil.disk_usage(ROOT).free>=10*1024**3,'MIN_FREE10GIB'

def clean_ids(d):return d['schemes']+d.get('source_extra_schemes',[])
def scenario_ids(d,scale):return d['schemes'] if scale else clean_ids(d)

def scenarios(d):
    return [('WHOLE_K1_REF_SCALE'+str(scale),scale) for scale in d['scales']]+[(SOURCE_NAME,None)]

def declare():
    d=candidate();verify_bound();inputs=c.load(OUT/'configs/holdout_inputs.lock.json')
    assert inputs['status']=='NATIVE_VERIFIED_FRESH_INPUTS_AFTER_CANDIDATE_FREEZE'
    assert inputs['candidate']==c.ref(OUT/'configs/CONFIRMATION_CANDIDATE.lock.json') and inputs['input_master_base']==9515480000
    assert len(inputs['programs'])==3
    for item in inputs['programs']:
        for key in ['binary','input','native_stdout']:assert c.sha(ROOT/item[key])==item[key+'_sha256']
    own=OUT/'configs/CHUNK2.lock.json'
    content=dict(status='FIXED_BEFORE_ANY_CHUNK2_CPU',phase_counts=dict(HOLDOUT_CLEAN=3*len(clean_ids(d)),HOLDOUT_FAULT=36+6*len(clean_ids(d))),planned_cpu=36+9*len(clean_ids(d)),chunk_cap=120,original_global_used_before_v9=3009,original_global_cpu_cap=3200,global_core_hours_cap=108,new_v9_core_hours_cap=12,new_disk_gib=8,combined_disk_gib=34,shared_slots32=True,first_pilot_trials=2,
        candidate=c.ref(OUT/'configs/CONFIRMATION_CANDIDATE.lock.json'),inputs=c.ref(OUT/'configs/holdout_inputs.lock.json'),producer=c.ref(OUT/'configs/PRODUCER.lock.json'),chunk1=c.ref(OUT/'configs/ROUND1.lock.json'),development_analysis=d['development_analysis'],development_maps=c.ref(OUT/'configs/DEVELOPMENT_maps.lock.json'),
        helpers={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__).resolve(),ROOT/'scripts/native_v9_confirm_analyze.py',ROOT/'scripts/native_v9_holdout_inputs.py']},scenarios=scenarios(d),schemes=d['schemes'],source_extra_schemes=d.get('source_extra_schemes',[]),owners_per_program_scenario=2,owner_master_base=9615480000,input_master_base=9515480000,clock_Hz=2000000000,cycle_ticks=500,horizon='4*maximum selected-scheme actual clean cycles per fresh program',whole='Historical1.05e-14 cm2/bit*20/cm2/hour/3600*scale; K1; same all6 union envelope and absent-site thinning',source='CHARM multiplicity205SBU:9K2 with assumed2000 events/second; uniform valid contiguous logical raw ages. Distinct from v8 event-count-normalized1/A stress; not a measured mission rate or physical layout.',failure_retention=POLICY,inference='Fresh input and independent owner, N2/cell exploratory nominal95; no superiority/equivalence or all-four best-by-region claim',no_hardware_cost_claim=True)
    if own.exists():assert c.load(own)==content,'CHUNK2_DECLARATION_CHANGED'
    else:
        assert not phase_markers();check_budget(content['planned_cpu']);put(own,content)
    return content

def retained_failure(row):
    if row['phase']!='HOLDOUT_FAULT' or not row['scenario'].startswith(POLICY['scenario_prefix']) or row['status']!='FAIL_EXECUTION' or row.get('cycles') is not None or row.get('exit_code') in [None,0,-999]:return None
    log=(ROOT/row['output']/'gem5.log').read_text(errors='replace')
    types=re.findall(r"terminate called after throwing an instance of '([^']+)'",log)
    messages=re.findall(r'^\s*what\(\):\s*([^\r\n]+)\s*$',log,re.M)
    for kind in types:
        for message in messages:
            if kind in POLICY['exception_types'] and message.strip() in POLICY['messages']:return dict(classification='OBSERVED_WHOLE_DECODER_UNCORRECTABLE',exception_type=kind,message=message.strip(),causal3plus_proven=False)
    translated=re.findall(r'^RuntimeError: ([^\r\n]+)$',log,re.M)
    trace1=re.search(r'^\s*src/python/m5/simulate\.py\([0-9]+\): simulate\s*$',log,re.M)
    trace2=re.search(r'^\s*'+re.escape(str(c.CONFIG))+r'\([0-9]+\): <module>\s*$',log,re.M)
    if trace1 and trace2:
        for message in translated:
            if message in POLICY['messages']:return dict(classification='OBSERVED_WHOLE_DECODER_UNCORRECTABLE',exception_type='RuntimeError pybind translation; CXX subtype unavailable',message=message,causal3plus_proven=False)
    return None

def workers_limit(requested):
    assert 1<=requested<=32
    tools=set()
    for process in Path('/proc').iterdir():
        if not process.name.isdigit():continue
        try:
            exe=(process/'exe').resolve();cwd=(process/'cwd').resolve()
            if exe.name in ['genus','innovus'] and cwd.is_relative_to(ROOT):tools.add(exe.name)
        except (OSError,RuntimeError):pass
    return min(requested,32-4*len(tools))

def execute(tasks,name,workers):
    declaration=declare();producer=verify_bound();assert len(tasks)==declaration['phase_counts'][name]
    report=OUT/'reports'/(name+'.json');lock=OUT/'configs'/(name+'.lock.json')
    assert not report.exists() and not lock.exists(),'IMMUTABLE_CONFIRMATION_PHASE'
    put(lock,dict(status='FROZEN_BEFORE_CHUNK2_DISPATCH',tasks=tasks,chunk2=c.ref(OUT/'configs/CHUNK2.lock.json'),binary_sha256=producer['binary_sha256'],config_sha256=producer['config_sha256']))
    c.cpu.OUT=OUT;c.cpu.BINARY=c.BINARY;c.cpu.CONFIG=c.CONFIG
    workers=workers_limit(workers);result=[];offset=0
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        while offset<len(tasks):
            width=min(2 if offset==0 else workers,len(tasks)-offset);check_budget(width)
            # Existing run_one uses shared32 leases and timeout-safe child groups.
            batch=list(pool.map(c.run_one,tasks[offset:offset+width]));offset+=width
            for row in batch:
                retained=retained_failure(row)
                if retained:row['retained_fault_failure']=retained
                result.append(row)
                with (OUT/'EXPERIMENT_LEDGER.jsonl').open('a') as stream:stream.write(json.dumps({key:row.get(key) for key in ['phase','label','status','output','started_at','ended_at','host_cpu_seconds','max_rss_kib','command','failure','retained_fault_failure']})+'\n')
                print(name,len(result),row['label'],row['status'],row.get('failure'),flush=True)
            failures=[r for r in result if r['status']!='PASS'];stops=[r for r in failures if not r.get('retained_fault_failure')]
            c.write(report,dict(status='STOPPED_RETAINED' if stops else 'RUNNING',planned=len(tasks),actual_runs=len(result),not_started=len(tasks)-len(result),tasks=result))
            if stops:raise RuntimeError(('CHUNK2_AFFECTED_PHASE_STOPPED_RAW_RETAINED',name,[r['label'] for r in stops]))
            if offset==width:
                valid=[r for r in batch if r['status']=='PASS'];assert valid,'PILOT_HAS_NO_VALID_EXECUTIONS'
                peak=max(r['max_rss_kib'] for r in valid);available=next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
                assert peak*workers<available/2,'CHUNK2_PILOT_MEMORY'
                put(OUT/'reports'/(name+'_PILOT_SPEED.json'),dict(status='PASS',actual_runs=width,max_rss_kib=peak,mean_host_cpu_seconds=sum(r['host_cpu_seconds'] for r in valid)/len(valid),authorized_workers=workers))
    c.write(report,dict(status='FAIL_RETAINED' if failures else 'PASS',planned=len(tasks),actual_runs=len(result),not_started=0,tasks=result))
    return result

def clean(workers):
    d=candidate();declare();items=c.load(OUT/'configs/holdout_inputs.lock.json')['programs']
    rows=execute([c.make(item,ident,'HOLDOUT_CLEAN') for item in items for ident in clean_ids(d)],'HOLDOUT_CLEAN',workers)
    for item in items:
        reference=next(r for r in rows if r['program']==item['name'] and r['id']=='U')
        for row in (r for r in rows if r['program']==item['name']):
            for field in ['cycles','instructions']:assert row[field]==reference[field],('HOLDOUT_NATIVE_CLEAN_EXECUTION',row['label'],field)
            for field in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']:assert row['seu'][field]==reference['seu'][field],('HOLDOUT_NATIVE_CLEAN_STATE',row['label'],field)
    put(OUT/'reports/HOLDOUT_CLEAN_ACCEPTANCE.json',dict(status='PASS_FRESH_INPUT_PREDECLARED_NATIVE_NORMAL',source=c.ref(OUT/'reports/HOLDOUT_CLEAN.json'),full_instruction_retired_audit=False,normal_stage_fit_is_assumed=True))

def plan_faults():
    d=candidate();declare();assert c.load(OUT/'reports/HOLDOUT_CLEAN_ACCEPTANCE.json')['status'].startswith('PASS')
    items=c.load(OUT/'configs/holdout_inputs.lock.json')['programs'];rows=c.load(OUT/'reports/HOLDOUT_CLEAN.json')['tasks'];cm={(r['program'],r['id']):r for r in rows}
    maps=c.load(OUT/'configs/DEVELOPMENT_maps.lock.json')['maps'];assert set(maps)==set(c.IDS)
    for item in items:
        for ident in clean_ids(d):assert semantic_map(c.load(ROOT/cm[item['name'],ident]['output']/'logical_manifest.json'))==maps[ident]
    union=sorted(set().union(*(set(m) for m in maps.values())))
    raw=next(w['site_ids'] for w in c.load(ROOT/'sources/protection_scope.lock.json')['payload_words'] if len(w['site_ids'])==130)
    owners=[];tasks=[]
    for wi,item in enumerate(items):
        name=item['name']
        for si,(scenario,scale) in enumerate(scenarios(d)):
            active_ids=scenario_ids(d,scale);H=max(cm[name,ident]['cycles'] for ident in active_ids)
            for n in range(2):
                master=9615480000+wi*1000000+si*10000+n;tt,ll,kk=rng(master,'time'),rng(master,'location'),rng(master,'K');events={ident:[] for ident in active_ids};latent=[];cycle=0.
                rate=(1.05e-14*20/3600*scale)*len(union)/2e9 if scale else 2000/2e9
                while True:
                    cycle+=float(tt.exponential(1/rate))
                    if cycle>4*H:break
                    tick=max(1,int(round(cycle*500)))
                    if scale:
                        key=union[int(ll.integers(len(union)))];latent.append(dict(tick=tick,K=1,site_key=key))
                        for ident in active_ids:
                            if key in maps[ident]:events[ident].append(dict(tick=tick,sites=[maps[ident][key]]))
                    else:
                        K=1 if float(kk.random())<205/214 else 2;age=int(ll.integers(131-K));sites=raw[age:age+K];latent.append(dict(tick=tick,K=K,raw_age=age,sites=sites))
                        for ident in active_ids:events[ident].append(dict(tick=tick,sites=sites))
                owner=f'V9_CONFIRMATION.{si}.{n}'
                owners.append(dict(program=name,scenario=scenario,scale=scale,owner=owner,master=master,time=descriptor(master,'time'),location=descriptor(master,'location'),K=descriptor(master,'K'),clock_Hz=2000000000,cycle_ticks=500,clean_max_cycles=H,cap_cycles=4*H,lambda_union_per_cycle=rate if scale else None,lambda_source_events_per_cycle=rate if not scale else None,perbit_rate_per_second=(1.05e-14*20/3600*scale) if scale else None,source_expected_K=(205+2*9)/214 if not scale else None,populations={ident:len(maps[ident]) for ident in active_ids},all6_union_size=len(union),latent=latent,accepted=events))
                for ident in active_ids:
                    tape=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events[ident]);task=c.make(item,ident,'HOLDOUT_FAULT',scenario,owner,tape,expected=cm[name,ident]['instructions']);task['tape_horizon_ticks']=4*H*500;tasks.append(task)
    return owners,tasks

def fault(workers):
    owners,tasks=plan_faults();path=OUT/'configs/HOLDOUT_owners.lock.json'
    put(path,dict(status='FIXED_BEFORE_CHUNK2_FAULTS',candidate=c.ref(OUT/'configs/CONFIRMATION_CANDIDATE.lock.json'),inputs=c.ref(OUT/'configs/holdout_inputs.lock.json'),clean=c.ref(OUT/'reports/HOLDOUT_CLEAN.json'),maps=c.ref(OUT/'configs/DEVELOPMENT_maps.lock.json'),all6_union_thinning=True,owners=owners))
    execute(tasks,'HOLDOUT_FAULT',workers)
    c.note('L0.CONFIRMATION','Fresh-input/owner fixed cohort terminal; source and whole contracts separate','Analyze signed pairs, failures, censoring and rates without pooling development','No best-by-region, physical superiority or equivalence inference from N2')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['declare','clean','fault'],required=True);parser.add_argument('--workers',type=int,default=32);args=parser.parse_args()
    if args.phase=='declare':declare();print('PASS chunk2 predeclared; no simulation from declaration')
    elif args.phase=='clean':clean(args.workers)
    else:fault(args.workers)

if __name__=='__main__':main()
