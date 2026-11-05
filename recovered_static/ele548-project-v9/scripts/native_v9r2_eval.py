"""Future fixed-all-six R2 evaluation, preparation permitted, dispatch gated.

This script NEVER creates BUDGET_AMENDMENT.lock.json. A later explicit user
budget authorization, recorded and bound by root, is necessary for clean/fault.
No old source, configuration, producer, attempt, or evidence is overwritten.
"""
import argparse, concurrent.futures, datetime, json, re, shutil, traceback
from pathlib import Path
import native_v9_common as c
import native_v9r2_gate as g2
from native_v9_campaign import semantic_map
from rng_namespace import rng, descriptor

ROOT=c.ROOT
OUT=ROOT/'rate_state_v9/r2_evaluation/runtime'
BINARY=g2.BINARY
CONFIG=g2.CONFIG
SOURCE='SOURCE_RAW130_CHARM_2000S'
SINGLE='RAW130_K2_SINGLE'
SCENARIOS=[SOURCE,'WHOLE_K1_REF_SCALE1000000000000000','WHOLE_K1_REF_SCALE10000000000000000',SINGLE]
COUNTS={'EVAL_CLEAN':18,'EVAL_FAULT':144}
INPUT_MASTER=10015480000
OWNER_MASTER=10615480000
REQUIRED_GLOBAL_CAP=3361

def put(path,data):
    assert not path.exists(),('IMMUTABLE_R2_EVALUATION',str(path))
    c.write(path,data)

def checked(value):
    path=ROOT/value['path'];assert path.is_file() and c.sha(path)==value['sha256'],('BOUND_REFERENCE_CHANGED',value)
    return path

def verify_producer():
    g2.verify()
    path=g2.OUT/'configs/PRODUCER.lock.json';producer=c.load(path)
    assert producer['status']=='PASS_BOUNDED_R2_CORRECTNESS13_NOT_FULL_CAMPAIGN_QUALIFICATION'
    assert producer['actual_cpu_attempts']==13
    for binding in producer['acceptance'].values():assert c.load(checked(binding))['status'].startswith('PASS')
    built=c.load(checked(producer['built']))
    assert c.sha(BINARY)==built['binary']['sha256'] and c.sha(CONFIG)==built['config']['sha256']
    checked(built['source']);checked(built['build_log']);checked(built['build_time'])
    return producer,built

def all_starts():
    return list((ROOT/'rate_state_v9').glob('**/reports/run_starts/*.json'))
def own_starts():
    return list((OUT/'reports/run_starts').glob('*.json'))

def freeze_proposal():
    producer,built=verify_producer()
    path=OUT/'configs/PROPOSAL.lock.json'
    document=dict(status='NOT_EXECUTED_NEEDS_BUDGET_AMENDMENT',planned_cpu=162,phase_counts=COUNTS,
      fixed_schemes=c.IDS,scheme_parameters=c.V,no_candidate_tuning_or_postselection=True,
      producer=c.ref(g2.OUT/'configs/PRODUCER.lock.json'),source=built['source'],binary=built['binary'],config=built['config'],
      source_scope=c.ref(ROOT/'sources/protection_scope.lock.json'),
      scenarios=SCENARIOS,input_master_base=INPUT_MASTER,owner_master_base=OWNER_MASTER,
      owner_rule='base+program_index*1000000+scenario_index*10000+owner_index;2owners/cell; namespacev2 roles time/location/K unchanged',
      programs=['qsort_small','dijkstra_small','sha1'],fresh_input_sizes=dict(qsort=2000,dijkstra_nodes=100,sha_payload_bytes=131072),
      proposal_reason='R2 common native152bit metadata endpoint passed bounded correctness; original performance comparisons remain R1. Evaluate all6 on fresh inputs and owners, with a separately labelled conditionalK2 stratum.',
      whole='K1, actual R2 ALL6 semantic union, absent-site thinning, historical1.05e-14cm2/bit*20/cm2/hour/3600*scale, scales1e15/1e16',
      source_fault_contract='Assumed2000events/s at2GHz=>1e-6events/cycle; K=1 if int(Krng.integers(214))<205 else2; uniform valid contiguous logical raw130 age; atomic event; no E[K] division or reroll.',
      conditional='RAW130_K2_SINGLE is exactlyone forcedK2 with time uniform in1..cleanUcycles*500 and age uniform0..128. Mechanistic conditional stratum, never relabelled as naturally sampled CHARM.',
      clock_Hz=2000000000,cycle_ticks=500,tape_horizon='4*max actual clean cycles across all6 for each fresh program; real elapsed ticks through program termination; futureevents retained',
      timing='Frozen nativeL0/II0/LEGACY/C0/U0, normal encode/decode stage-fit assumed, selected-protection repair4cycles and common endpoint correction>=1cycle; not physical latency/PPA.',
      fairness='Common native metadata coding is common transport integrity, not S* recovery gain; source raw130 and whole augmented predictor/storage populations remain separate.',
      old_global_cpu_cap=3200,required_new_global_cpu_cap=REQUIRED_GLOBAL_CAP,expected_prior_actual_global=3199,expected_global_after162=3361,
      new_evaluation_cpu_cap=162,new_v9_core_hours_cap=12,global_core_hours_cap=108,new_worktree_disk_gib=8,combined_disk_gib=34,min_free_gib=10,shared_slot_cap=32,initial_pilot_trials=2,
      failure_policy='Every decoder/metadata/assertion/timeout/unsupportedISA/syscall failure keeps raw and nullcycles; stop affected stage. No failure is a masked event. No imputation or favorable rejection. No automatic retry.',
      inference='2independent owners/cell; paired signed B-D and fixed-all6 comparison; exploratory nominalCI only. Fresh inputs of3fixedprograms, not new-program or SPEC-score generalization.',
      helpers={str(p.relative_to(ROOT)):c.sha(p) for p in [Path(__file__).resolve(),ROOT/'scripts/native_v9r2_eval_inputs.py',ROOT/'scripts/native_v9r2_gate.py',ROOT/'scripts/native_v9_common.py',ROOT/'scripts/v3_cpu_common.py',ROOT/'scripts/v3_common.py',ROOT/'scripts/rng_namespace.py',ROOT/'scripts/native_v9_campaign.py']})
    if path.exists():assert c.load(path)==document,'PROPOSAL_CHANGED_AFTER_FREEZE'
    else:
        assert not own_starts(),'EVALUATION_ALREADY_STARTED'
        # This is a proposal, never authorization to exceed the old cap.
        put(path,document)
    return document

def verify_prepared():
    document=freeze_proposal();prepared=c.load(OUT/'configs/PREPARED.lock.json')
    assert prepared['status']=='PREPARED_NO_GEM5_TRIALS_NEEDS_BUDGET_AMENDMENT'
    assert prepared['proposal']==c.ref(OUT/'configs/PROPOSAL.lock.json')
    checked(prepared['inputs']);inputs=c.load(OUT/'configs/inputs.lock.json')
    assert inputs['proposal']==prepared['proposal'] and inputs['input_master_base']==INPUT_MASTER
    for item in inputs['programs']:
        for field in ['binary','input','native_stdout']:checked(dict(path=item[field],sha256=item[field+'_sha256']))
    return document,inputs

def authorization():
    proposal,_=verify_prepared();path=OUT/'configs/BUDGET_AMENDMENT.lock.json'
    assert path.is_file(),('BUDGET_NOT_AUTHORIZED',str(path),'prepare is permitted; clean/fault require a later explicit user authorization recorded by root')
    amendment=c.load(path)
    assert amendment['status']=='USER_AUTHORIZED_R2_EVALUATION_162'
    assert amendment['authorized_by']=='user'
    assert amendment['prior_global_cpu_cap']==3200 and amendment['new_global_cpu_cap']==REQUIRED_GLOBAL_CAP and amendment['evaluation_cpu_budget']==162
    assert amendment['proposal']==c.ref(OUT/'configs/PROPOSAL.lock.json') and amendment['producer']==c.ref(g2.OUT/'configs/PRODUCER.lock.json')
    user=amendment['user_authorization']
    assert user.get('evidence_origin')=='current_user_message','CURRENT_USER_MESSAGE_REQUIRED'
    assert all(isinstance(user.get(field),str) and user[field].strip() for field in ['observed_at_utc','instruction_excerpt']),'EXPLICIT_LATER_USER_AUTHORIZATION_REQUIRED'
    # Optional turn_id is recorded only when the host actually provides one.
    assert amendment.get('new_v9_core_hours_cap',12)==12 and amendment.get('global_core_hours_cap',108)==108,'COMPUTE_TIME_AUTHORITY_NOT_IMPLIED'
    assert amendment.get('new_worktree_disk_gib',8)==8 and amendment.get('combined_disk_gib',34)==34,'DISK_AUTHORITY_NOT_IMPLIED'
    return amendment

def budget(reserve=0):
    authorization()
    assert not list((ROOT/'rate_state_v9').rglob('*.timeout.json')),'UNRESOLVED_TIMEOUT_RESOURCE_ACCOUNTING'
    assert 3009+len(all_starts())+reserve<=REQUIRED_GLOBAL_CAP,'AMENDED_GLOBAL3361_CPU_CAP'
    assert len(own_starts())+reserve<=162,'NEW_EVALUATION162_CAP'
    historical=[p for p in all_starts() if not p.is_relative_to(OUT)]
    assert 3009+len(historical)==3199,'HISTORICAL_ATTEMPT_BASE_CHANGED_NEEDS_REVISED_AUTHORIZATION'
    seconds=c.used_seconds();gib=c.disk_gib()
    assert seconds<12*3600 and 65.39845555555556+seconds/3600<108,'UNCHANGED_CORE_HOUR_CAP'
    assert gib<8 and gib+20.54370880126953<34,'UNCHANGED_DISK_CAP'
    assert shutil.disk_usage(ROOT).free>=10*1024**3,'MIN_FREE10GIB'

def prepare():
    proposal=freeze_proposal()
    assert not (OUT/'configs/PREPARED.lock.json').exists(),'IMMUTABLE_PREPARATION'
    from native_v9r2_eval_inputs import generate
    if not (OUT/'configs/inputs.lock.json').exists():generate()
    inputs=c.load(OUT/'configs/inputs.lock.json')
    assert inputs['proposal']==c.ref(OUT/'configs/PROPOSAL.lock.json')
    actual=3009+len(all_starts());assert actual==3199 and not own_starts(),'EXPECTED_PRIOR_GLOBAL3199'
    put(OUT/'configs/PREPARED.lock.json',dict(status='PREPARED_NO_GEM5_TRIALS_NEEDS_BUDGET_AMENDMENT',proposal=c.ref(OUT/'configs/PROPOSAL.lock.json'),inputs=c.ref(OUT/'configs/inputs.lock.json'),producer=c.ref(g2.OUT/'configs/PRODUCER.lock.json'),planned_cpu=162,actual_global_before=actual,old_global_cap=3200,required_new_global_cap=3361,authorization_file_absent=not (OUT/'configs/BUDGET_AMENDMENT.lock.json').exists(),native_answer_checks_are_not_gem5_trials=True))
    print('PREPARED162; no gem5 trials; explicit later budget authorization still required')

def run(task):
    with c.slot():
        started=datetime.datetime.now(datetime.timezone.utc).isoformat();marker=OUT/'reports/run_starts'/(task['phase']+'.'+task['label']+'.json')
        put(marker,dict(phase=task['phase'],label=task['label'],started_at=started,producer=c.ref(g2.OUT/'configs/PRODUCER.lock.json')))
        try:
            row=c.cpu.run_cpu(task)
            if row['status']=='PASS':
                folder=ROOT/row['output'];log=(folder/'gem5.log').read_text(errors='replace');s=row['seu']
                if re.search(r'instruction .*unimplemented|ignoring syscall|unimplemented syscall',log,re.I):row.update(status='FAIL_VALIDATION',failure='UNSUPPORTED_ISA_OR_SYSCALL')
                if task.get('tape_horizon_ticks') and s['end_tick']>task['tape_horizon_ticks']:row.update(status='FAIL_VALIDATION',failure='TAPE_HORIZON_EXCEEDED')
                for prefix in ['hot','shadow','journal']:
                    if prefix+'_accepted' in s and s[prefix+'_accepted']!=s[prefix+'_completed']+s[prefix+'_cancelled']+s[prefix+'_pending']:row.update(status='FAIL_VALIDATION',failure=prefix.upper()+'_CONSERVATION')
        except Exception as error:
            folder=OUT/'reports'/task['phase']/task['label'];folder.mkdir(parents=True,exist_ok=True);(folder/'runner_exception.txt').write_text(traceback.format_exc())
            row={k:v for k,v in task.items() if k not in ['input','events_text']};row.update(status='FAIL_RUNNER',failure=repr(error),cycles=None,exit_code=None,output=str(folder.relative_to(ROOT)),producer_binary_sha256=c.sha(BINARY),config_sha256=c.sha(CONFIG),host_cpu_seconds=None,max_rss_kib=None)
        row.update(started_at=started,ended_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
        folder=ROOT/row['output']
        if row['status']!='PASS':row['cycles']=None
        row.setdefault('hashes',{}).update({p.name:c.sha(p) for p in folder.iterdir() if p.is_file()})
        return row

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

def execute(tasks,phase,workers):
    proposal,_=verify_prepared();authorization();budget(len(tasks));verify_producer()
    assert len(tasks)==COUNTS[phase]
    put(OUT/'configs'/(phase+'.lock.json'),dict(status='FROZEN_BEFORE_AUTHORIZED_EVALUATION_PHASE',tasks=tasks,proposal=c.ref(OUT/'configs/PROPOSAL.lock.json'),prepared=c.ref(OUT/'configs/PREPARED.lock.json'),authorization=c.ref(OUT/'configs/BUDGET_AMENDMENT.lock.json'),producer=c.ref(g2.OUT/'configs/PRODUCER.lock.json')))
    report=OUT/'reports'/(phase+'.json');assert not report.exists(),'IMMUTABLE_PHASE'
    c.cpu.OUT=OUT;c.cpu.BINARY=BINARY;c.cpu.CONFIG=CONFIG
    rows=[];offset=0;workers=workers_limit(workers)
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        while offset<len(tasks):
            width=min(2 if offset==0 else workers,len(tasks)-offset);budget(width)
            rows.extend(pool.map(run,tasks[offset:offset+width]));offset+=width
            failed=[r for r in rows if r['status']!='PASS']
            c.write(report,dict(status='STOPPED_RETAINED' if failed else ('PASS' if offset==len(tasks) else 'RUNNING'),planned=len(tasks),actual_runs=len(rows),not_started=len(tasks)-len(rows),tasks=rows))
            for row in rows[-width:]:
                with (OUT/'EXPERIMENT_LEDGER.jsonl').open('a') as stream:stream.write(json.dumps({key:row.get(key) for key in ['phase','label','status','output','started_at','ended_at','host_cpu_seconds','max_rss_kib','failure','command']})+'\n')
            print(phase,len(rows),'/',len(tasks),'failures',len(failed),flush=True)
            if failed:raise RuntimeError(('R2_EVALUATION_AFFECTED_STAGE_STOPPED_RAW_RETAINED',phase,[r['label'] for r in failed]))
            if offset==width:
                peak=max(r['max_rss_kib'] for r in rows);available=next(int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith('MemAvailable:'))
                assert peak*workers<available/2,'PILOT_MEMORY'
                put(OUT/'reports'/(phase+'_PILOT_SPEED.json'),dict(status='PASS',actual_runs=width,max_rss_kib=peak,mean_host_cpu_seconds=sum(r['host_cpu_seconds'] for r in rows)/width,authorized_workers=workers))
    return rows

def clean(workers):
    _,inputs=verify_prepared();authorization()
    rows=execute([c.make(item,ident,'EVAL_CLEAN') for item in inputs['programs'] for ident in c.IDS],'EVAL_CLEAN',workers)
    for item in inputs['programs']:
        ref=next(r for r in rows if r['program']==item['name'] and r['id']=='U')
        for row in (r for r in rows if r['program']==item['name']):
            for field in ['cycles','instructions']:assert row[field]==ref[field],('R2_CLEAN_EXECUTION_DIFFERENCE',row['label'],field)
            for field in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws']:assert row['seu'][field]==ref['seu'][field],('R2_CLEAN_STATE_DIFFERENCE',row['label'],field)
            assert row['seu']['native_pending_bits']==152 and row['seu']['native_pending_repairs']==0
    put(OUT/'reports/CLEAN_ACCEPTANCE.json',dict(status='PASS_FRESH_ALL_SIX_NATIVE_NORMAL',source=c.ref(OUT/'reports/EVAL_CLEAN.json'),physical_stage_fit='ASSUMED_NOT_MEASURED'))

def fault_plan():
    _,inputs=verify_prepared();authorization();assert c.load(OUT/'reports/CLEAN_ACCEPTANCE.json')['status'].startswith('PASS')
    rows=c.load(OUT/'reports/EVAL_CLEAN.json')['tasks'];cm={(r['program'],r['id']):r for r in rows};items=inputs['programs']
    maps={ident:semantic_map(c.load(ROOT/cm[items[0]['name'],ident]['output']/'logical_manifest.json')) for ident in c.IDS}
    for item in items:
        for ident in c.IDS:assert semantic_map(c.load(ROOT/cm[item['name'],ident]['output']/'logical_manifest.json'))==maps[ident]
    union=sorted(set().union(*(set(m) for m in maps.values())))
    raw=next(w['site_ids'] for w in c.load(ROOT/'sources/protection_scope.lock.json')['payload_words'] if len(w['site_ids'])==130)
    jobs=[];owners=[]
    for wi,item in enumerate(items):
        program=item['name'];A=cm[program,'U']['cycles'];H=max(cm[program,ident]['cycles'] for ident in c.IDS)
        for si,scenario in enumerate(SCENARIOS):
            for index in range(2):
                master=OWNER_MASTER+wi*1000000+si*10000+index;tt,ll,kk=rng(master,'time'),rng(master,'location'),rng(master,'K');latent=[];events={ident:[] for ident in c.IDS}
                scale=10**15 if scenario==SCENARIOS[1] else 10**16 if scenario==SCENARIOS[2] else None
                rate=(1.05e-14*20/3600*scale)*len(union)/2e9 if scale else 2000/2e9 if scenario==SOURCE else None
                if scenario==SINGLE:
                    tick=max(1,int(tt.integers(1,A*500+1)));age=int(ll.integers(129));sites=raw[age:age+2];latent=[dict(tick=tick,K=2,raw_age=age,sites=sites)]
                    for ident in c.IDS:events[ident]=[dict(tick=tick,sites=sites)]
                else:
                    cycle=0.
                    while True:
                        cycle+=float(tt.exponential(1/rate))
                        if cycle>4*H:break
                        tick=max(1,int(round(cycle*500)))
                        if scale:
                            key=union[int(ll.integers(len(union)))];latent.append(dict(tick=tick,K=1,site_key=key))
                            for ident in c.IDS:
                                if key in maps[ident]:events[ident].append(dict(tick=tick,sites=[maps[ident][key]]))
                        else:
                            K=1 if int(kk.integers(214))<205 else 2;age=int(ll.integers(131-K));sites=raw[age:age+K];latent.append(dict(tick=tick,K=K,raw_age=age,sites=sites))
                            for ident in c.IDS:events[ident].append(dict(tick=tick,sites=sites))
                owner=f'R2_EVALUATION.{si}.{index}'
                owners.append(dict(program=program,scenario=scenario,owner=owner,master=master,time=descriptor(master,'time'),location=descriptor(master,'location'),K=descriptor(master,'K'),clock_Hz=2000000000,cycle_ticks=500,A_clean_U_cycles=A,H_max_clean_cycles=H,cap_cycles=4*H,scale=scale,lambda_union_or_source_per_cycle=rate,conditional_single_K2=scenario==SINGLE,populations={ident:len(maps[ident]) for ident in c.IDS},union_size=len(union),latent=latent,accepted=events))
                for ident in c.IDS:
                    tape=''.join(str(e['tick'])+' '+';'.join(map(str,e['sites']))+'\n' for e in events[ident]);task=c.make(item,ident,'EVAL_FAULT',scenario,owner,tape,expected=cm[program,ident]['instructions']);task['tape_horizon_ticks']=4*H*500;jobs.append(task)
    assert len(jobs)==144 and len(owners)==24
    return maps,owners,jobs

def fault(workers):
    maps,owners,tasks=fault_plan()
    put(OUT/'configs/MAPS.lock.json',dict(status='ACTUAL_R2_ALL6_CLEAN_MANIFESTS_BEFORE_EVENTS',maps=maps,producer=c.ref(g2.OUT/'configs/PRODUCER.lock.json'),clean=c.ref(OUT/'reports/EVAL_CLEAN.json')))
    put(OUT/'configs/OWNERS.lock.json',dict(status='FIXED_BEFORE_AUTHORIZED_R2_FAULT_DISPATCH',owners=owners,maps=c.ref(OUT/'configs/MAPS.lock.json'),proposal=c.ref(OUT/'configs/PROPOSAL.lock.json'),authorization=c.ref(OUT/'configs/BUDGET_AMENDMENT.lock.json')))
    execute(tasks,'EVAL_FAULT',workers)
    print('All R2 evaluation tasks terminal; independent bound analysis remains required. No winner is inferred by this runner.')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['prepare','clean','fault'],required=True);parser.add_argument('--workers',type=int,default=32);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='clean':clean(args.workers)
    else:fault(args.workers)

if __name__=='__main__':main()
