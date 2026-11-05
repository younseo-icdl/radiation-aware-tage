#!/usr/bin/env python3
"""Audit actual12 replication, matched signed ABCD, no simulator or RNG."""
from pathlib import Path
from collections import defaultdict
import csv, datetime, hashlib, json, subprocess, sys
BASE=Path(__file__).resolve().parents[1]; REPORT=BASE/'reports'
V10=Path('/home/youns/workspace/ele548-project-v10')
def load(p):return json.loads(Path(p).read_text())
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ref(p):return {'path':str(p),'sha256':sha(p)}
def checked(v):
    assert sha(v['path'])==v['sha256'],('CHANGED_EVIDENCE',v['path']);return Path(v['path'])
def put(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n')
def csvwrite(name,rows):
    with (REPORT/name).open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
    raw_path=REPORT/'FAULT12.json';raw=load(raw_path)
    assert raw['status']=='PASS_ACTUAL12_FAULT_REPLICATION_NOT_INDEPENDENT_OR_COST_QUALIFICATION'
    assert raw['completed']==12 and raw['resources']['actual_global_CPU']==3487
    plan=load(checked(raw['plan']));checked(plan['runner']);checked(plan['config']);checked(plan['binary'])
    proposal=load(checked(plan['proposal']));checked(plan['authorization'])
    old_fault_path=checked(proposal['source_fault_report']);old_fault=load(old_fault_path)
    normal_path=checked(proposal['CPU_gate']);normal=load(normal_path)
    normal_plan=load(checked(normal['plan']));old_clean_path=checked(normal_plan['old_report'])
    clean=load(old_clean_path)
    old_faults={(r['program'],r['R'],r['owner'],r['policy']):r for r in old_fault['tasks']}
    old_cleans={(r['program'],r['R'],r['policy']):r for r in clean['tasks']}
    new_cleans={(r['program'],r['R']):r for r in normal['tasks']}
    policies=['U','C_PAR_FREQUENT','C_PAR_PERIODIC','C_ECC','C_TMR','A_DIR']
    pairs=[];contrasts=[];failures=[];raw_checked=0
    for row in raw['tasks']:
        for filename,expected in row['hashes'].items():
            assert sha(Path(row['output'])/filename)==expected,('RAW_CHANGED',row['label'],filename)
            raw_checked+=1
        if row['status']!='PASS_PROGRAM_AND_EXACT_LOGICAL_INJECTION':
            failures.append({'label':row['label'],'status':row['status'],'cycles':None});continue
        key=(row['program'],row['R']);owner=row['owner'];b=old_faults[*key,owner,'U']
        assert b['status']=='PASS'
        c=new_cleans[key];a=old_cleans[*key,'U']
        direct=old_faults[*key,owner,'A_DIR']
        assert row['instructions']==c['instructions']==a['instructions']
        assert c['cycles']==a['cycles']
        task=next(t for t in plan['tasks'] if t['label']==row['label'])
        assert sha(Path(row['output'])/'schedule.ticks')==task['schedule']['sha256']
        assert row['hashes']['schedule.ticks']==b['hashes']['schedule.ticks']
        valid=row['seu']['applied_events']==b['seu']['applied_events']==1
        # A censored event is retained and explicitly excluded, never a zero.
        delta=row['cycles']-c['cycles'] if valid else None
        net=b['cycles']-row['cycles'] if valid else None
        p={'program':key[0],'R':key[1],'owner':owner,'pair_valid':valid,
           'A':a['cycles'],'B':b['cycles'],'C':c['cycles'],'D':row['cycles'],
           'normal_overhead_C_minus_A':c['cycles']-a['cycles'],
           'fault_increment_D_minus_C':delta,'net_B_minus_D':net,
           'net_percent_of_A':100*net/a['cycles'] if valid else None,
           'D_equal_C':row['cycles']==c['cycles'],
           'canonical_fingerprint_equal_clean':row['seu']['canonical_base_state_hash']==c['seu']['canonical_base_state_hash'],
           'D_equal_direct_cycles':row['cycles']==direct['cycles'],
           'canonical_fingerprint_equal_direct':row['seu']['canonical_base_state_hash']==direct['seu']['canonical_base_state_hash'],
           'predictor_rng_equal_direct':row['seu']['predictor_rng_hash']==direct['seu']['predictor_rng_hash'],
           'predictor_rng_equal_clean':row['seu']['predictor_rng_hash']==c['seu']['predictor_rng_hash'],
           'active_fold_phi_mismatch_words':row['seu']['fold_phi_mismatch_words'],
           'exposed_bits':row['total_bits'],'actual_applied_events':row['seu']['applied_events']}
        pairs.append(p)
        for policy in policies:
            baseline=old_faults[*key,owner,policy];assert baseline['status']=='PASS'
            assert baseline['hashes']['schedule.ticks']==row['hashes']['schedule.ticks']
            both_valid=valid and baseline['seu']['applied_events']==1
            diff=baseline['cycles']-row['cycles'] if both_valid else None
            contrasts.append({'program':key[0],'R':key[1],'owner':owner,'comparator':policy,
                              'pair_valid':both_valid,'baseline_D':baseline['cycles'],'overwrite_D':row['cycles'],
                              'baseline_minus_overwrite_cycles':diff,
                              'percent_of_A':100*diff/a['cycles'] if both_valid else None})
    assert not failures and len(pairs)==12
    csvwrite('FAULT12_ABCD.csv',pairs);csvwrite('FAULT12_CONTRASTS.csv',contrasts)
    groups=defaultdict(list)
    for row in pairs:groups[row['program'],row['R']].append(row)
    summaries=[]
    for (program,R),rows in groups.items():
        good=[r for r in rows if r['pair_valid']];n=len(good)
        assert n==2,'PREDECLARED_TWO_OWNER_PAIR_INCOMPLETE'
        nets=[r['net_B_minus_D'] for r in good]
        summary={'program':program,'R':R,'valid_owners':n,'A':good[0]['A'],
                 'mean_B_minus_D':sum(nets)/n,'mean_net_percent_of_A':sum(r['net_percent_of_A'] for r in good)/n,
                 'mean_D_minus_C':sum(r['fault_increment_D_minus_C'] for r in good)/n,
                 'owner_net_min':min(nets),'owner_net_max':max(nets),
                 'n2_empirical_bootstrap_lower':min(nets),'n2_empirical_bootstrap_upper':max(nets),
                 'D_equal_C_count':sum(r['D_equal_C'] for r in good),
                 'cycles_equal_direct_count':sum(r['D_equal_direct_cycles'] for r in good),
                 'hash_equal_direct_count':sum(r['canonical_fingerprint_equal_direct'] for r in good),
                 'hash_equal_clean_count':sum(r['canonical_fingerprint_equal_clean'] for r in good)}
        summaries.append(summary)
    csvwrite('FAULT12_PROGRAM_SUMMARY.csv',summaries)
    contrast_summary=[]
    for program,R in groups:
        for policy in policies:
            rows=[r for r in contrasts if (r['program'],r['R'],r['comparator'])==(program,R,policy) and r['pair_valid']]
            assert len(rows)==2
            xs=[r['baseline_minus_overwrite_cycles'] for r in rows]
            contrast_summary.append({'program':program,'R':R,'comparator':policy,'n':2,
                                     'mean_baseline_minus_overwrite_cycles':sum(xs)/2,
                                     'mean_percent_of_A':sum(r['percent_of_A'] for r in rows)/2,
                                     'paired_min':min(xs),'paired_max':max(xs)})
    csvwrite('FAULT12_CONTRAST_SUMMARY.csv',contrast_summary)
    # Resource function verifies terminal counts and existing limits without
    # importing/running any main dispatcher or changing its frozen source.
    import importlib.util
    s=importlib.util.spec_from_file_location('resource_only',BASE/'tools/run_fault12.py')
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);resources=m.resources()
    assert resources['inflight_reserved_coreh']==0 and resources['actual_global_CPU']==3487
    put(REPORT/'FAULT12_FINAL_GATES.json',{
        'status':'PASS_ACTUAL12_AUDITED_PAIRED_REPLICATION_NOT_INDEPENDENT_COST_OR_HARDWARE_QUALIFICATION',
        'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'actual_global_CPU':3487,'CPU_cap':3487,
        'new_fault_runs':12,'valid_ABCD_pairs':sum(r['pair_valid'] for r in pairs),'raw_SHA_checked':raw_checked,
        'failures':failures,'resources':resources,'source_plan':ref(REPORT/'FAULT12_PLAN.lock.json'),
        'old_baselines_reused':{'clean':ref(old_clean_path),'fault':ref(old_fault_path)},
        'new_clean':ref(normal_path),'new_fault':ref(raw_path),
        'analysis_tool':ref(Path(__file__)),'program_summary':summaries,'contrasts':contrast_summary,
        'independence':'Existing six program/owner tuples reused across R1/R8 and all policies; not12 independent owners or new holdout',
        'interval_scope':'n2 exact empirical percentile bootstrap endpoints equal observed owner min/max. Exploratory only, no95% population coverage, equivalence or noninferiority claim.',
        'full_research_goal':'ACTIVE_NOT_COMPLETE','hardware_qualified_candidates':0})
    table='\n'.join(f"|{r['program']}|{r['R']}|{r['mean_B_minus_D']:,.1f}|{r['mean_net_percent_of_A']:.6f}%|{r['mean_D_minus_C']:,.1f}|{r['hash_equal_clean_count']}/2|" for r in summaries)
    compare_table='\n'.join(f"|{r['program']}|{r['R']}|{r['comparator']}|{r['mean_baseline_minus_overwrite_cycles']:,.1f}|{r['paired_min']:,}…{r['paired_max']:,}|" for r in contrast_summary if r['comparator']!='U')
    report=f'''# Overwrite 오류 CPU12회 — 실제 개발 replication

## DONE

사용자 승인 “3,487회로 확대하고12회 진행”을 기록하고 기존6 owner/tick/site의 raw130 single-SBU를 같은 R1/R8 프로그램·입력으로 새 producer에서12회 실행했다. 초기2개 통과 후 나머지10개를 병렬 실행했다.12회 모두 프로그램 정답·실제 XOR·schedule/config·queue conservation gate PASS다. 새 raw SHA {raw_checked}개와12 matched A/B/C/D를 검산했다. 기존6방식과 정상 실행은 재실행/덮어쓰기하지 않았다.

## 프로그램별 관측

A/B=기존 무보호 정상/오류, C/D=새 overwrite 정상/오류 cycles다. 양의 B−D는 같은 사건의 오류 무보호보다 overwrite가 빨랐다는 뜻이다. C=A는 C0 정상 회귀 관측이며 실제 물리 유지 비용0의 증거가 아니다.

|프로그램|R|평균 B−D cycles|평균 순이득 (% of A)|평균 D−C cycles|종료 canonical hash=clean|
|---|---:|---:|---:|---:|---:|
{table}

각 프로그램/R은 owner2개다. Owner별 signed 값, helpful/zero와 paired empirical bootstrap endpoints는 CSV/FINAL_GATES에 보존했다. n2 endpoints는 관측 두 값의 min/max로 formal95% coverage나 모집단 우위/동등성 증명이 아니다. R1/R8의 같은 owner를 독립 표본으로 다시 세지 않는다.

### 모든 기존 보호와 대조

아래 `baseline D−overwrite D`가 양수면 overwrite가 해당 baseline보다 빠르다. 기존 baseline의 normal/check/repair 계약은 그대로다. Direct에만 유리한 지연을 부여하거나 parity/ECC/TMR의 비용을 추가하지 않았다.

U=P0, C_PAR_FREQUENT=빈번 P_ED, C_PAR_PERIODIC=주기 k64 P_ED, C_ECC=SECDED, C_TMR=TMR, A_DIR=exact direct다. 정상 check/encode/vote와 source 유지의 C0 stage-fit은 가정이다. 기존 보호의 오류 repair4와 overwrite/direct의 repair0 계약을 그대로 보존했지만 full-overwrite의 실제 유한 지연을 측정한 비교는 아니다. 이 표로 실제 하드웨어 우위를 선언하지 않는다.

|프로그램|R|기존 비교군|평균 baseline−overwrite cycles|paired owner 범위|
|---|---:|---|---:|---:|
{compare_table}

Cycles 같음은 저장소 완전 동일성이나 이후 무해함을 보장하지 않는다. Canonical hash는 fingerprint이며 전체 storage의 bit 비교도 아니다. Active fold 일관성·RNG·잔여 state 차이는 `FAULT12_ABCD.csv`에 분리했다. 손상 상태의 위치와 프로그램 종료 이후 영향은 아직 미확정이다.

Overwrite와 exact direct 사이에도 cycles·canonical fingerprint·RNG를 별도로 대조했다. Cycle 차이가0이어도 두 구조의 source ownership·storage·timing이나 모든 branch prediction stream이 같다는 증명은 아니다.

## 비용 해석과 다음 결정

**IMPLEMENTED/TESTED RESULT:** 이번은 source 손상 후 full-fold overwrite의 CPU 동작 통합 gate다. 실제 원시값에서 기존 보호 대비 유리/불리한 프로그램·owner를 모두 보고한다. 작은 C++ fixed stream의 이득을 CPU 승리로 일반화하지 않는다.

**ASSUMPTION / NOT DONE:** Native L0/C0 synchronous source/reduction/encode/check/vote stage-fit은 가정이다. Finite overwrite stage·실제 operand sampling/visibility·ports/II/queue/backpressure, 독립 input/owner 평가, WHOLE 추가 storage 노출은 이12회에 없다. 기존 S*=346bits의 P0/P_ED/P_ECC/P_TMR·frequent/periodic parity·exact direct를 유지하며 새 RTL/Cadence/SPICE/TCAD는0이다. Hardware-qualified 후보도0이다.

CPU의 full-fold 작업/lookup은 정상 qsort 약1.21, dijkstra 약1.21, sha1 약1.00이다. 임의의 추가 폭/port를 가정하지 않고 실제130 source bits/912 tap terms/200 fold 쓰기와 undo 부담을 비용 입력으로 사용한다. 다음은 lookup/source/update 비용을 공통 경계에서 비교하는 finite-stage 설계·정확성 gate다. 평균 operation 계수만으로 stall/CPI·면적·에너지를 확정하지 않는다. Functional 우위가 없는 조건에서는 비용 하한/실패 조건도 결과로 남긴다.

## 실행 예산·보존·NEXT

Actual global3487/3487, 새 fault12, 실패0, 남은 CPU 할당0이다. V11 recorded {resources['v11_recorded_coreh']:.6f}/2.5coreh, 합산 {resources['combined_recorded_coreh']:.6f}/16, global {resources['global_recorded_coreh']:.6f}/108coreh다. 원본 transport/source/binary/archive와 이전 성공·실패를 보존했다. 이전 정상gate의3475상한/미승인12 문서는 당시의 동결 기록이며 최신 권한은 BUDGET_AMENDMENT_3487, 실제 완료는 이보고서/FAULT12_FINAL_GATES다.

추가 independent126회·reserve6·새 CPU timing 변형을 발행하지 않았다. 전체 연구 goal은active이며 새로운 CPU실행은 별도 구체적상한 전까지없다. 현재 결과 분석과 finite timing 설계는 계속할 수 있다.
'''
    with (REPORT/'FAULT12_FINAL_REPORT.ko.md').open('x') as f:f.write(report)
    print(json.dumps({'status':'PASS_ACTUAL12_MATCHED_ANALYSIS','pairs':len(pairs),'program_summary':summaries,'resources':resources}))
if __name__=='__main__':main()
