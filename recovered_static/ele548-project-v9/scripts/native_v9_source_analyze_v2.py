"""Analyze the completed conditional RAW130 cohort; WHOLE failure stays separate."""
import csv, hashlib, io, itertools, json, statistics
from pathlib import Path
import numpy as np
import native_v9_common as c
from native_v9_confirm import SOURCE_NAME

ROOT,BASE=c.ROOT,c.OUT;CONT=ROOT/'rate_state_v9/source_continuation/runtime';DEST=ROOT/'rate_state_v9/results/source_complete_v2'
IDS=['U','C_PAR_FREQUENT','A_DIR','C_ECC','C_TMR'];CHECKED={}
def check(p,h=None):
    p=Path(p);d=c.sha(p)
    if h:assert d==h,('RAW_CHANGED',str(p))
    CHECKED[str(p.relative_to(ROOT))]=d
def csv_text(rows):
    f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=list(dict.fromkeys(k for r in rows for k in r)));w.writeheader();w.writerows(rows);return f.getvalue()
def interval(values):
    # Exhaustive nonparametric n=2 paired bootstrap; no artificial branch samples.
    assert len(values)==2
    means=[statistics.mean(v) for v in itertools.product(values,repeat=2)]
    return float(np.quantile(means,.025,method="inverted_cdf")),float(np.quantile(means,.975,method="inverted_cdf"))
def main():
    assert not DEST.exists(),'IMMUTABLE_SOURCE_ANALYSIS'
    d=c.load(CONT/'reports/SOURCE_CONTINUATION.json');assert d['status']=='PASS' and len(d['tasks'])==20
    partial=c.load(BASE/'reports/HOLDOUT_FAULT.json');assert partial['status']=='STOPPED_RETAINED'
    rows=[r for r in partial['tasks'] if r['scenario']==SOURCE_NAME]+d['tasks'];assert len(rows)==30
    clean={(r['program'],r['id']):r for r in c.load(BASE/'reports/HOLDOUT_CLEAN.json')['tasks']}
    keyed={(r['program'],r['owner'],r['id']):r for r in rows};assert len(keyed)==30
    locked={t['label']:t for t in c.load(BASE/'configs/HOLDOUT_FAULT.lock.json')['tasks']}
    raw=set(next(w['site_ids'] for w in c.load(ROOT/'sources/protection_scope.lock.json')['payload_words'] if len(w['site_ids'])==130))
    for r in rows:
        assert r['status']=='PASS';t=locked[r['label']]
        assert r['producer_binary_sha256']==c.load(BASE/'configs/PRODUCER.lock.json')['binary_sha256']
        assert (ROOT/r['output']/'schedule.ticks').read_text()==t['events_text']
        for name,h in r['hashes'].items():check(ROOT/r['output']/name,h)
        s=r['seu'];events=list(csv.DictReader((ROOT/r['output']/'events.csv').open()))
        assert len(events)==s['applied_events'] and s['end_tick']<=t['tape_horizon_ticks']
        for event in events:assert set(map(int,event['site_ids'].split(';')))<=raw and event['XOR_verified']=='1'
    abcd=[];summary=[];comparisons=[]
    for program in ['qsort_small','dijkstra_small','sha1']:
        owners=sorted({r['owner'] for r in rows if r['program']==program});assert len(owners)==2
        for ident in IDS:
            paired=[]
            for owner in owners:
                r=keyed[program,owner,ident];u=keyed[program,owner,'U'];a=clean[program,'U'];cl=clean[program,ident]
                A,B,C,D=a['cycles'],u['cycles'],cl['cycles'],r['cycles'];s=r['seu']
                row=dict(program=program,scenario=SOURCE_NAME,owner=owner,policy=ident,A=A,B=B,C=C,D=D,normal_overhead_pct=100*(C-A)/A,fault_increment=D-C,total_slowdown_pct=100*(D-A)/A,net_gain_cycles=B-D,net_gain_pp=100*(B-D)/A,helpful=D<C,zero_damage=D==C,no_event=s['applied_events']==0,applied_events=s['applied_events'],applied_K2_events=s['applied_flips']-s['applied_events'],future_events=s['unapplied_future_events'],terminal_state_mismatch=s['canonical_base_state_hash']!=cl['seu']['canonical_base_state_hash'],raw=r['output'])
                abcd.append(row);paired.append(row)
            values=[r['net_gain_pp'] for r in paired];low,high=interval(values)
            summary.append(dict(level='PROGRAM_SCENARIO',program=program,scenario=SOURCE_NAME,policy=ident,n_planned=2,n_valid_pairs=2,common_owner_mean_net_gain_pp=statistics.mean(values),mean_net_gain_pp=statistics.mean(values),CI_low_pp=low,CI_high_pp=high,mean_fault_increment_cycles=statistics.mean(r['fault_increment'] for r in paired),mean_total_slowdown_pct=statistics.mean(r['total_slowdown_pct'] for r in paired),helpful=sum(r['helpful'] for r in paired),zero_damage=sum(r['zero_damage'] for r in paired),no_event=sum(r['no_event'] for r in paired),applied_events=sum(r['applied_events'] for r in paired),applied_K2_events=sum(r['applied_K2_events'] for r in paired),terminal_mismatch=sum(r['terminal_state_mismatch'] for r in paired),inference='N2 exact paired nonparametric bootstrap descriptive only; no superiority/equivalence/safety claim'))
        for ident in ['C_PAR_FREQUENT','C_ECC','C_TMR']:
            values=[100*(keyed[program,o,ident]['cycles']-keyed[program,o,'A_DIR']['cycles'])/clean[program,'U']['cycles'] for o in owners];low,high=interval(values)
            comparisons.append(dict(program=program,conventional=ident,mean_direct_advantage_pp=statistics.mean(values),CI_low_pp=low,CI_high_pp=high,n=2,sign='positive means direct uses fewer fault cycles',inference='Fixed source scenario only; WHOLE failure excluded from this estimand, not erased'))
    report=['# R1 조건부 raw-history 독립 확인 — 중단과 별도인 SOURCE30회\n\n','원래 WHOLE 실패 row/부분49회/미발행32회를 그대로 보존했다. 그중 미발행 SOURCE20회만 새 scope amendment로 이어 실제 SOURCE30회가 모두 완료됐다. 입력·owner·K/시각/site·source/config/binary는 원래 fault 전 동결값과 같다. 프로그램마다 owner2개이므로 탐색 결과이며 최종 우위/동등성을 확정하지 않는다.\n\n','|program|policy|B−D %p [nominal95]|total slowdown %|events/K2|\n|---|---|---:|---:|---:|\n']
    for r in summary:report.append(f'|{r["program"]}|{r["policy"]}|{r["mean_net_gain_pp"]:+.5f} [{r["CI_low_pp"]:+.5f},{r["CI_high_pp"]:+.5f}]|{r["mean_total_slowdown_pct"]:+.5f}|{r["applied_events"]}/{r["applied_K2_events"]}|\n')
    report.append('\n같은 owner tape의 다섯 replay를 다섯 독립 사건으로 세지 않는다. K2수는 실제 applied_flips−applied_events(K∈{1,2})이며 종료 후 사건은 포함하지 않는다. raw130 조건은 전체S*346/path/fold/metadata를 모두 공격한 조건이 아니다. R1 WHOLE pending.active 실패는 남아 있으므로 이 표로 metadata 안전성/전체환경 승자를 주장하지 않는다. 정상stage-fit C0와4cycle 보호복구는 가정이고 full PPA는UNKNOWN이다.\n')
    artifacts={'SOURCE_ABCD.csv':csv_text(abcd),'SOURCE_SUMMARY.csv':csv_text(summary),'SOURCE_CONVENTIONAL_MINUS_DIRECT.csv':csv_text(comparisons),'SOURCE_REPORT.ko.md':''.join(report)}
    DEST.mkdir(parents=True)
    for name,value in artifacts.items():(DEST/name).write_text(value)
    c.write(DEST/'ANALYSIS.lock.json',dict(status='PASS_COMPLETE_SOURCE30_WITH_SEPARATE_PRESERVED_WHOLE_FAILURE',original_partial=c.ref(BASE/'reports/HOLDOUT_FAULT.json'),continuation=c.ref(CONT/'reports/SOURCE_CONTINUATION.json'),scope_amendment=c.ref(CONT/'configs/SCOPE_AMENDMENT.lock.json'),checked_raw=CHECKED,source_cpu=30,new_continuation_cpu=20,script=c.ref(Path(__file__)),artifacts_sha256={k:hashlib.sha256(v.encode()).hexdigest() for k,v in artifacts.items()}))
    print('PASS SOURCE30 complete; WHOLE failure retained separately')
if __name__=='__main__':main()
