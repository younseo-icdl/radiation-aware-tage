"""Bind actual independent-input/owner chunk2 evidence; never dispatch.

N=2 owners per fixed program/scenario gives exploratory paired bootstrap only.
All failed/unstarted cases, zero/helpful effects, and future events are retained.
"""
import collections, configparser, csv, datetime, hashlib, io, json, math, statistics
from pathlib import Path
import numpy as np
import native_v9_common as c
from native_v9_confirm import (candidate, checked_ref, clean_ids, scenario_ids,
    scenarios, retained_failure, verify_bound, SOURCE_NAME, PHASES)
from native_v9_campaign import semantic_map
from rng_namespace import descriptor

ROOT,OUT=c.ROOT,c.OUT
RESULTS=ROOT/'rate_state_v9/results/confirmation'
BOOTSTRAP_SEED=9725480000
BOOTSTRAP_DRAWS=10000
VERIFIED={}

def verify(path,digest=None):
    path=Path(path);name=str(path.relative_to(ROOT));actual=c.sha(path)
    if digest is not None:assert actual==digest,('CONFIRMATION_RAW_CHANGED',name)
    if name in VERIFIED:assert VERIFIED[name]==actual
    VERIFIED[name]=actual
    return actual

def key(row):return tuple(row[k] for k in ['program','scenario','owner','id'])
def csv_text(rows,fields):
    stream=io.StringIO(newline='');keys=list(dict.fromkeys(fields+[k for row in rows for k in row]));writer=csv.DictWriter(stream,fieldnames=keys);writer.writeheader();writer.writerows(rows);return stream.getvalue()
def equal(a,b,field):return None if field not in a or field not in b else a[field]==b[field]
def ci(values,indices):
    array=np.asarray(values,dtype=float);draws=array[indices].mean(axis=1)
    return float(array.mean()),float(np.quantile(draws,.025)),float(np.quantile(draws,.975)),draws

def verified_phases():
    d=candidate();producer=verify_bound();chunk=c.load(OUT/'configs/CHUNK2.lock.json')
    assert chunk['status']=='FIXED_BEFORE_ANY_CHUNK2_CPU'
    for name in ['candidate','inputs','producer','chunk1','development_analysis','development_maps']:verify(checked_ref(chunk[name]),chunk[name]['sha256'])
    for name,digest in chunk['helpers'].items():verify(ROOT/name,digest)
    verify(c.BINARY,producer['binary_sha256']);verify(c.CONFIG,producer['config_sha256'])
    inputs=c.load(OUT/'configs/holdout_inputs.lock.json');items=inputs['programs'];maps=c.load(OUT/'configs/DEVELOPMENT_maps.lock.json')['maps']
    phase_rows={};task_maps={};bindings={};not_started=[]
    for phase in PHASES:
        lock_path=OUT/'configs'/(phase+'.lock.json');report_path=OUT/'reports'/(phase+'.json')
        locked=c.load(lock_path);report=c.load(report_path);verify(lock_path);verify(report_path)
        assert locked['chunk2']==c.ref(OUT/'configs/CHUNK2.lock.json')
        assert locked['status']=='FROZEN_BEFORE_CHUNK2_DISPATCH' and report['status'] in ['PASS','FAIL_RETAINED','STOPPED_RETAINED']
        assert locked['binary_sha256']==producer['binary_sha256'] and locked['config_sha256']==producer['config_sha256']
        expected={key(t):t for t in locked['tasks']};actual={key(r):r for r in report['tasks']}
        assert len(expected)==len(locked['tasks'])==chunk['phase_counts'][phase]
        assert len(actual)==len(report['tasks']) and set(actual)<=set(expected)
        assert report['actual_runs']==len(actual) and report['not_started']==len(expected)-len(actual)
        if report['status']!='STOPPED_RETAINED':assert set(actual)==set(expected)
        for missing in sorted(set(expected)-set(actual)):
            task=expected[missing];not_started.append(dict(phase=phase,program=task['program'],scenario=task['scenario'],owner=task['owner'],policy=task['id'],status='NOT_STARTED_AFTER_AFFECTED_PHASE_STOP',cycles=None))
        for identity,row in actual.items():
            task=expected[identity];folder=ROOT/row['output'];assert row['producer_binary_sha256']==producer['binary_sha256'] and row['config_sha256']==producer['config_sha256']
            assert (folder/'schedule.ticks').read_text()==task['events_text'];verify(folder/'schedule.ticks',row['schedule_sha256'])
            for field in ['binary','input','native_stdout']:verify(ROOT/task['input'][field],task['input'][field+'_sha256'])
            for name,digest in row['hashes'].items():verify(folder/name,digest)
            verify(folder/'gem5.log.time')
            config=configparser.ConfigParser();config.read(folder/'config.ini');params=config['system.cpu.branchPred.conditionalBranchPred.tage']
            for name,value in [('scheme',task['scheme']),('role_policy',task['policy']),('inspection_interval',str(task['k'])),('pipeline_mode','native'),('lookup_latency','0'),('lookup_ii','0'),('journal_service','false'),('resource_mode','LEGACY'),('check_cycles','0'),('maintenance_cycles','0'),('repair_cycles','0' if task['scheme']=='P0' else '4')]:assert params[name]==value,('ACTUAL_CONFIRMATION_CONFIG',row['label'],name)
            manifest=c.load(folder/'logical_manifest.json');assert semantic_map(manifest)==maps[row['id']]
            if row['status']=='PASS':
                assert row['exit_code']==0 and row['cycles']>0
                verify(folder/'program.stdout',task['input']['native_stdout_sha256']);assert not (folder/'program.stderr').read_bytes()
                assert c.load(folder/'seu.json')==row['seu'] and row['total_bits']==manifest['total_bits']
                if task.get('expected_instructions'):assert row['instructions']==task['expected_instructions']
                s=row['seu'];assert s['scheduled_events']==s['applied_events']+s['unapplied_future_events'];assert not s['oracle_cost'] and not s['journal_service']
                assert not task.get('tape_horizon_ticks') or s['end_tick']<=task['tape_horizon_ticks'],'EXPOSURE_CENSOR_CAP_EXCEEDED'
                applied=list(csv.DictReader((folder/'events.csv').open()));within=[line.split() for line in task['events_text'].splitlines() if int(line.split()[0])<=s['end_tick']]
                assert len(applied)==len(within)==s['applied_events']
                for event,(tick,ids) in zip(applied,within):assert event['tick']==tick and event['site_ids']==ids and event['XOR_verified']=='1'
            else:
                assert row.get('cycles') is None,'FAILED_CYCLE_IMPUTATION'
                if row.get('retained_fault_failure'):assert retained_failure(row)==row['retained_fault_failure'],'FAILURE_SIGNATURE_CHANGED'
        task_maps[phase]=expected;phase_rows[phase]=list(actual.values());bindings[phase]=dict(task_lock=c.ref(lock_path),report=c.ref(report_path),actual_runs=len(actual),not_started=len(expected)-len(actual))
    acceptance=OUT/'reports/HOLDOUT_CLEAN_ACCEPTANCE.json';assert c.load(acceptance)['status'].startswith('PASS');verify(acceptance)
    owner_path=OUT/'configs/HOLDOUT_owners.lock.json';owners=c.load(owner_path);verify(owner_path)
    for name,path in [('candidate','CONFIRMATION_CANDIDATE.lock.json'),('inputs','holdout_inputs.lock.json'),('maps','DEVELOPMENT_maps.lock.json')]:assert owners[name]==c.ref(OUT/'configs'/path)
    assert owners['clean']==c.ref(OUT/'reports/HOLDOUT_CLEAN.json') and owners['all6_union_thinning']
    om={(r['program'],r['scenario'],r['owner']):r for r in owners['owners']};assert len(om)==18
    development={r['master'] for r in c.load(OUT/'configs/DEVELOPMENT_owners.lock.json')['owners']};assert not development.intersection(r['master'] for r in om.values())
    cm={(r['program'],r['id']):r for r in phase_rows['HOLDOUT_CLEAN']}
    union=sorted(set().union(*(set(m) for m in maps.values())))
    raw=next(w['site_ids'] for w in c.load(ROOT/'sources/protection_scope.lock.json')['payload_words'] if len(w['site_ids'])==130)
    for wi,item in enumerate(items):
        for si,(scenario,scale) in enumerate(scenarios(d)):
            active=scenario_ids(d,scale);H=max(cm[item['name'],ident]['cycles'] for ident in active)
            for n in range(2):
                owner=f'V9_CONFIRMATION.{si}.{n}';spec=om[item['name'],scenario,owner];master=9615480000+wi*1000000+si*10000+n
                assert spec['master']==master and spec['cap_cycles']==4*H and spec['clock_Hz']==2000000000 and spec['cycle_ticks']==500
                for role in ['time','location','K']:assert spec[role]==descriptor(master,role)
                assert spec['all6_union_size']==len(union) and spec['populations']=={ident:len(maps[ident]) for ident in active}
                rate=(1.05e-14*20/3600*scale)*len(union)/2e9 if scale else 2000/2e9
                assert spec['lambda_union_per_cycle' if scale else 'lambda_source_events_per_cycle']==rate
                expected_events={ident:[] for ident in active}
                previous=0
                for event in spec['latent']:
                    assert previous<=event['tick']<=4*H*500;previous=event['tick']
                    if scale:
                        assert event['K']==1 and event['site_key'] in union
                        for ident in active:
                            if event['site_key'] in maps[ident]:expected_events[ident].append(dict(tick=event['tick'],sites=[maps[ident][event['site_key']]]))
                    else:
                        assert event['K'] in [1,2] and 0<=event['raw_age']<=130-event['K']
                        assert event['sites']==raw[event['raw_age']:event['raw_age']+event['K']]
                        for ident in active:expected_events[ident].append(dict(tick=event['tick'],sites=event['sites']))
                assert spec['accepted']==expected_events
                for ident in active:
                    task=task_maps['HOLDOUT_FAULT'][item['name'],scenario,owner,ident]
                    expected_tape=''.join(str(event['tick'])+' '+';'.join(map(str,event['sites']))+'\n' for event in expected_events[ident])
                    assert task['events_text']==expected_tape and task['tape_horizon_ticks']==4*H*500
    return d,chunk,items,phase_rows,task_maps,om,bindings,not_started

def main():
    d,chunk,items,phases,tasks,owners,bindings,not_started=verified_phases()
    assert not RESULTS.exists(),'IMMUTABLE_CONFIRMATION_ANALYSIS'
    cm={(r['program'],r['id']):r for r in phases['HOLDOUT_CLEAN']};fm={key(r):r for r in phases['HOLDOUT_FAULT']}
    abcd=[];failures=[];rates=[];counters=[]
    for phase,rows in phases.items():
        for row in rows:
            if row['status']!='PASS':failures.append(dict(phase=phase,program=row['program'],scenario=row['scenario'],owner=row['owner'],policy=row['id'],status=row['status'],exit_code=row.get('exit_code'),failure=row.get('failure'),classification=row.get('retained_fault_failure',{}).get('classification'),cycles=None,raw=row['output']))
            s=row.get('seu',{});counters.append(dict(phase=phase,program=row['program'],scenario=row['scenario'],owner=row['owner'],policy=row['id'],status=row['status'],cycles=row.get('cycles'),IPC=row.get('IPC'),prediction_reads=s.get('prediction_reads'),checks=s.get('checks'),detected=s.get('detected'),corrected=s.get('corrected'),DUE=s.get('DUE'),reset_refill=s.get('reset_refill'),repair_batches=s.get('repair_batches'),response_hold_cycles=s.get('response_hold_cycles'),source_head_repairs=s.get('source_head_repairs'),source_metadata_hold_cycles=s.get('source_metadata_hold_cycles'),counter_sums_are_not_causal_CPI=True))
    for identity,task in tasks['HOLDOUT_FAULT'].items():
        program,scenario,owner,ident=identity;row=fm.get(identity);br=fm.get((program,scenario,owner,'U'));ar=cm[program,'U'];cr=cm[program,ident];spec=owners[program,scenario,owner]
        valid=all(r is not None and r['status']=='PASS' for r in [ar,br,cr,row]);s=(row or {}).get('seu',{});ownclean=cr.get('seu',{})
        A=ar.get('cycles');B=(br or {}).get('cycles');C=cr.get('cycles');D=(row or {}).get('cycles')
        result=dict(program=program,scenario=scenario,owner=owner,policy=ident,status=(row or {}).get('status','NOT_STARTED'),reference_status=(br or {}).get('status','NOT_STARTED'),pair_valid=valid,A=A,B=B,C=C,D=D,logical_bits=(row or {}).get('total_bits'),end_tick=s.get('end_tick'),scheduled_events=s.get('scheduled_events'),applied_events=s.get('applied_events'),unapplied_future_events=s.get('unapplied_future_events'),latent_events_to_horizon=len(spec['latent']),absent_site_latent_rejections=len(spec['latent'])-len(spec['accepted'][ident]),horizon_ticks=task['tape_horizon_ticks'],terminal_base_matches_own_clean=equal(s,ownclean,'canonical_base_state_hash'),terminal_rng_matches_own_clean=equal(s,ownclean,'predictor_rng_hash'),normal_stage_fit_assumed=True,post_termination_damage_tail='RIGHT_CENSORED_UNKNOWN')
        if valid:
            result.update(net_gain_cycles=B-D,net_gain_pp=100*(B-D)/A,normal_overhead_pct=100*(C-A)/A,candidate_fault_increment_cycles=D-C,unprotected_fault_increment_cycles=B-A,fault_increment_reduction_cycles=(B-A)-(D-C),fault_increment_reduction_pp=100*((B-A)-(D-C))/A,total_slowdown_pct=100*(D-A)/A,helpful_fault=D<C,zero_damage=D==C,no_applied_event=s['applied_events']==0)
        abcd.append(result)
        expected_rate=(spec['perbit_rate_per_second']*spec['populations'][ident]/2e9) if spec['scale'] else spec['lambda_source_events_per_cycle']
        duration=s.get('end_tick',0)/500 if row and row['status']=='PASS' else None
        rate=dict(program=program,scenario=scenario,owner=owner,policy=ident,master=spec['master'],event_rate_per_cycle=expected_rate,perbit_rate_per_second=spec['perbit_rate_per_second'],expected_K=1 if spec['scale'] else (205+2*9)/214,clean_H_cycles=spec['clean_max_cycles'],expected_events_in_clean_H=expected_rate*spec['clean_max_cycles'],expected_events_to_4H=expected_rate*spec['cap_cycles'],probability_zero_events_in_clean_H=math.exp(-expected_rate*spec['clean_max_cycles']),probability_one_event_in_clean_H=(expected_rate*spec['clean_max_cycles'])*math.exp(-expected_rate*spec['clean_max_cycles']),actual_duration_cycles=duration,expected_events_over_actual_duration_descriptive=expected_rate*duration if duration is not None else None,applied_events=s.get('applied_events'),applied_flips=s.get('applied_flips'),source_rate_is_assumed2000_persecond=not bool(spec['scale']),duration_is_outcome_dependent_not_independent_exposure=True)
        rates.append(rate)
    grouped=collections.defaultdict(list)
    for row in abcd:grouped[row['program'],row['scenario']].append(row)
    summaries=[];draws_by_cell={};comparison_rows=[]
    for wi,item in enumerate(items):
        for si,(scenario,scale) in enumerate(scenarios(d)):
            rows=grouped[item['name'],scenario];policies=scenario_ids(d,scale)
            complete_owners=sorted({r['owner'] for r in rows if all(next(x for x in rows if x['owner']==r['owner'] and x['policy']==ident)['pair_valid'] for ident in policies)})
            indices=np.random.default_rng(BOOTSTRAP_SEED+wi*1000+si).integers(len(complete_owners),size=(BOOTSTRAP_DRAWS,len(complete_owners))) if complete_owners else None
            for ident in policies:
                selected=sorted([r for r in rows if r['policy']==ident],key=lambda r:r['owner']);valid=[r for r in selected if r['pair_valid']]
                out=dict(level='PROGRAM_SCENARIO',program=item['name'],scenario=scenario,policy=ident,n_planned=len(selected),n_valid_pairs=len(valid),n_invalid_pairs=len(selected)-len(valid),n_common_complete_owners=len(complete_owners),inference='N2_EXPLORATORY_NOMINAL95_NOT_SUPERIORITY_OR_EQUIVALENCE',helpful_owners=sum(r.get('helpful_fault',False) for r in valid),zero_damage_owners=sum(r.get('zero_damage',False) for r in valid),no_applied_event_owners=sum(r.get('no_applied_event',False) for r in valid),future_events=sum(r.get('unapplied_future_events',0) for r in valid),final_base_mismatch_owners=sum(r['terminal_base_matches_own_clean'] is False for r in valid))
                if valid:out.update(mean_net_gain_pp=statistics.mean(r['net_gain_pp'] for r in valid),mean_net_gain_cycles=statistics.mean(r['net_gain_cycles'] for r in valid),normal_overhead_pct=valid[0]['normal_overhead_pct'],mean_fault_increment_cycles=statistics.mean(r['candidate_fault_increment_cycles'] for r in valid),mean_total_slowdown_pct=statistics.mean(r['total_slowdown_pct'] for r in valid))
                if complete_owners:
                    values=[next(r['net_gain_pp'] for r in selected if r['owner']==owner) for owner in complete_owners];mean,low,high,draws=ci(values,indices);out.update(common_owner_mean_net_gain_pp=mean,CI_low_pp=low,CI_high_pp=high);draws_by_cell[item['name'],scenario,ident]=draws
                summaries.append(out)
            for owner in sorted({r['owner'] for r in rows}):
                for competitor in [p for p in policies if p not in ['U','A_DIR']]:
                    direct=next(r for r in rows if r['owner']==owner and r['policy']=='A_DIR');conv=next(r for r in rows if r['owner']==owner and r['policy']==competitor);valid=direct['pair_valid'] and conv['pair_valid']
                    out=dict(program=item['name'],scenario=scenario,owner=owner,conventional=competitor,pair_valid=valid,A=direct['A'],conventional_fault_cycles=conv['D'],direct_fault_cycles=direct['D'],inference='N2_FIXED_PREDECLARED_COMPARATOR_NOT_ALL_FOUR_BEST')
                    if valid:out.update(conventional_minus_direct_cycles=conv['D']-direct['D'],direct_advantage_pp=100*(conv['D']-direct['D'])/direct['A'])
                    comparison_rows.append(out)
            for competitor in [p for p in policies if p not in ['U','A_DIR']]:
                valid=[r for r in comparison_rows if r['program']==item['name'] and r['scenario']==scenario and r['conventional']==competitor and r['pair_valid']]
                out=dict(level='PROGRAM_SCENARIO_CONVENTIONAL_MINUS_DIRECT',program=item['name'],scenario=scenario,policy=competitor,n_valid_pairs=len(valid),n_planned=2,inference='N2_EXPLORATORY_NOMINAL95_PAIRED')
                if valid:out['mean_direct_advantage_pp']=statistics.mean(r['direct_advantage_pp'] for r in valid)
                if complete_owners:
                    direct_draws=draws_by_cell[item['name'],scenario,'A_DIR'];conv_draws=draws_by_cell[item['name'],scenario,competitor];difference=direct_draws-conv_draws;out.update(CI_low_pp=float(np.quantile(difference,.025)),CI_high_pp=float(np.quantile(difference,.975)))
                summaries.append(out)
    # Fixed-program macro per scenario; no pooling of owners across programs.
    for scenario,scale in scenarios(d):
        for ident in scenario_ids(d,scale):
            cells=[next(r for r in summaries if r['level']=='PROGRAM_SCENARIO' and r['program']==item['name'] and r['scenario']==scenario and r['policy']==ident) for item in items]
            out=dict(level='FIXED_PROGRAM_MACRO',program='MACRO_FIXED_EQUAL_PROGRAM_WEIGHT',scenario=scenario,policy=ident,n_planned=sum(r['n_planned'] for r in cells),n_valid_pairs=sum(r['n_valid_pairs'] for r in cells),inference='FIXED_PROGRAM_N2_PER_CELL_EXPLORATORY_NOMINAL95')
            if all((item['name'],scenario,ident) in draws_by_cell for item in items):
                draws=np.mean([draws_by_cell[item['name'],scenario,ident] for item in items],axis=0);out.update(mean_net_gain_pp=statistics.mean(r['common_owner_mean_net_gain_pp'] for r in cells),CI_low_pp=float(np.quantile(draws,.025)),CI_high_pp=float(np.quantile(draws,.975)))
            summaries.append(out)
    actual=sum(len(rows) for rows in phases.values());fail_count=len(failures)
    report=['# V9 독립 입력·owner 확인 실험\n\n',f'IMPLEMENTED/TESTED RESULT: 사전 고정 {chunk["planned_cpu"]}회 중 실제 {actual}회, 실행/검증 실패 {fail_count}회, 미실행 {len(not_started)}회를 보존했다. 개발108회 CPU 숫자를 합치지 않았다. 프로그램은 동일한 세 공개 프로그램이며 입력과 owner만 새로 생성했다.\n\n',f'고정 주비교는 U / {d["conventional_id"]} / A_DIR다. SOURCE에서만 사전 추가한 ECC/TMR을 비교하며 periodic parity는 개발 단계 결과만 있다. 새로운 MCU domain에서 모든 conventional의 최고를 선택했다는 주장은 하지 않는다.\n\n','A/B=정상/오류 U, C/D=정상/오류 방식. 순이득 B−D와 conventional faulty cycles−direct faulty cycles를 owner별로 계산했다. 정상 성분과 fault increment를 따로 보존했지만 차이의 차이는 노출/추측/학습 상호작용을 제거한 순수 복구 인과량이 아니다.\n\n','|프로그램|scenario|방식|유효/계획|B−D %p|nominal95 CI|helpful/zero/no-event|\n|---|---|---|---:|---:|---|---:|\n']
    for row in summaries:
        if row['level']!='PROGRAM_SCENARIO':continue
        value=f'{row["mean_net_gain_pp"]:+.5f}' if 'mean_net_gain_pp' in row else 'UNKNOWN';bounds=f'[{row["CI_low_pp"]:+.5f},{row["CI_high_pp"]:+.5f}]' if 'CI_low_pp' in row else 'UNKNOWN'
        report.append(f'|{row["program"]}|{row["scenario"]}|{row["policy"]}|{row["n_valid_pairs"]}/{row["n_planned"]}|{value}|{bounds}|{row["helpful_owners"]}/{row["zero_damage_owners"]}/{row["no_applied_event_owners"]}|\n')
    report.extend(['\nASSUMPTION: 정상 check/vote/maintenance가 기존 native L0 stage 안에 들어간다는 C0 가정, 보호법 repair4cycle 가정이다. 전체 보호법 실제 latency/PPA/전력/clock 우위는 검증하지 않았다.\n\n','WHOLE는 기존 per-bit arithmetic과 ALL6 공통 latent union/absent-site thinning을 유지한 K1 stress다. SOURCE는 205개의 K1 대9개의 K2 군집, 가정2000events/s, raw130의 유효 연속 logical age 주입이다. 사건 rate를 E[K]로 나누지 않았다. 이전1/A normalized stress와 rate가 다르며 실제 공간 배치·입자 단일사건·mission FIT로 해석하지 않는다.\n\n','각 프로그램/scenario의 owner는2개다. 10,000 paired bootstrap95% 구간은 탐색용이며 우위·동등성을 확정하지 않는다. 모든 comparator에 공통으로 유효한 owner를 resample했고, invalid pair와 생존자 선택은 별도로 표시했다. 무사건·helpful·zero·future 사건을 제거하지 않았다. 실제 종료 뒤 피해 tail은 right-censored UNKNOWN이다.\n\n','DONE: frozen 후보·입력·RNG·tape·source/config/producer와 각 raw SHA, 실제 설정·출력·사건/노출을 검증했다. NOT DONE: physical qualification, full-scheme cost, 모든 conventional의 새로운 domain별 tuning, 프로그램 모집단으로의 일반화. BLOCKERS/NEXT: 실패와 미실행이 있으면 raw를 보존하고 해당 gate를 우선 조사한다. 없으면 남은 실제 예산과 근거로 후속 실험/HDL 전 handoff를 결정한다.\n'])
    artifacts={'CPU_ABCD.csv':csv_text(abcd,['program','scenario','owner','policy','A','B','C','D','pair_valid']),'PAIRED_SUMMARY.csv':csv_text(summaries,['level','program','scenario','policy','n_planned','n_valid_pairs']),'CONVENTIONAL_MINUS_DIRECT.csv':csv_text(comparison_rows,['program','scenario','owner','conventional','pair_valid','conventional_minus_direct_cycles','direct_advantage_pp']),'RATE_EXPOSURE.csv':csv_text(rates,['program','scenario','owner','policy','event_rate_per_cycle','expected_events_in_clean_H','applied_events']),'COUNTERS.csv':csv_text(counters,['phase','program','scenario','owner','policy','status','cycles','IPC']),'EXECUTION_FAILURES.csv':csv_text(failures,['phase','program','scenario','owner','policy','status','exit_code','failure','cycles','raw']),'NOT_STARTED.csv':csv_text(not_started,['phase','program','scenario','owner','policy','status','cycles']),'CONFIRMATION_REPORT.ko.md':''.join(report)}
    lock=dict(status='PASS_BOUND_FRESH_INPUT_OWNER_EVIDENCE_NOT_PHYSICAL_OR_SUPERIORITY_QUALIFICATION',at=datetime.datetime.now(datetime.timezone.utc).isoformat(),actual_cpu_attempts=actual,planned_cpu_attempts=chunk['planned_cpu'],failures=fail_count,not_started=len(not_started),invalid_fault_pairs=sum(not r['pair_valid'] for r in abcd),phase_bindings=bindings,candidate=c.ref(OUT/'configs/CONFIRMATION_CANDIDATE.lock.json'),chunk2=c.ref(OUT/'configs/CHUNK2.lock.json'),owners=c.ref(OUT/'configs/HOLDOUT_owners.lock.json'),raw_hashes_verified=VERIFIED,bootstrap=dict(seed=BOOTSTRAP_SEED,draws=BOOTSTRAP_DRAWS,owners_per_cell=2,scheme_pairing='common complete owners',inference='N2_EXPLORATORY_ONLY'),old_and_development_cpu_results_not_pooled=True,artifacts_sha256={name:hashlib.sha256(value.encode()).hexdigest() for name,value in artifacts.items()},script=c.ref(Path(__file__)))
    artifacts['ANALYSIS.lock.json']=json.dumps(lock,indent=2,ensure_ascii=False)+'\n';RESULTS.mkdir(parents=True)
    for name,value in artifacts.items():(RESULTS/name).write_text(value)
    print('PASS chunk2 evidence analysis; actual',actual,'failures',fail_count,'not_started',len(not_started))

if __name__=='__main__':main()
