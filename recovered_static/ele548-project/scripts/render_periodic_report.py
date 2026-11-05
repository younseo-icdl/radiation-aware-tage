#!/usr/bin/env python3
"""Reproducible tables from audited outcomes; narrative source kept separately."""
import json
from pathlib import Path
from summarize_e3_cpu import sha
ROOT=Path(__file__).resolve().parents[1]
def main():
    r=json.loads((ROOT/'reports/PERIODIC_EXTENSION_SUMMARY.json').read_text())
    m=json.loads((ROOT/'reports/PERIODIC_MODEL_SUMMARY.json').read_text())
    assert r['status']=='PASS_AUDITED_PERIODIC_EXTENSION_PILOT' and m['status']=='PASS_AUDITED_CONDITIONAL_MODEL_HOLDOUT_PILOT'
    assert r['campaign_sha256']==sha(ROOT/'reports/PERIODIC_CPU_EVAL.json')
    assert m['campaign_sha256']==sha(ROOT/'reports/PERIODIC_MODEL_HOLDOUT.json')
    text=(ROOT/'docs/11_PERIODIC_METHOD.ko.md').read_text()
    def est(e):return f"{e['mean']:.6g} [{e['bootstrap95CI'][0]:.6g}, {e['bootstrap95CI'][1]:.6g}]"
    lines=['## IMPLEMENTED/TESTED RESULT — 같은 evaluation owners의 CPU 비용','',
        '조건: targeted S*346payload bits, CHARM6T equal-event λ=10⁻⁶/CPUcycle, C1/R4. P0는C0/R0 reference다. 추가 update-lane response latency는0 가정이다. 기존 baseline108개 raw records를 검증·재사용하고 새CPU42개를 audit했다. 고정2program 동일 가중이며 물리 rate나 silicon 성능이 아니다.','',
        '| Scheme | Clean overhead (%) | Total slowdown (%) | Net B−D (% of pristine, 95% CI) | Mean raw B−D cycles (95% CI) |',
        '|---|---:|---:|---:|---:|']
    for g in r['groups']:
        v=g['metrics'];lines.append(f"| {g['scheme']} | {v['clean_overhead_pct']['mean']:.6g} | {v['total_slowdown_pct']['mean']:.6g} | {est(v['net_benefit_pct_points'])} | {est(v['net_cycles_B_minus_D'])} |")
    lines += ['', '이 가정 아래 mean clean overhead는5.1903%에서0.2915%로 줄었다. k32의 total slowdown0.2783%, net benefit3.6033pp(CI2.2988–5.0624)다. Raw-cycles와 program별 pristine으로 normalized한 fixed-program 평균은 서로 다른 estimand다.', '',
        '| Program | P0 faulty slowdown (%) | k32 slowdown (%) | k32 net benefit (pp, 95% CI) |', '|---|---:|---:|---:|']
    p0=next(g for g in r['groups'] if g['scheme']=='P0');period=next(g for g in r['groups'] if g['scheme']=='P_PERIODIC_ED')
    for program,v in period['program_metrics'].items():
        lines.append(f"| {program} | {p0['program_metrics'][program]['total_slowdown_pct']['mean']:.6g} | {v['total_slowdown_pct']['mean']:.6g} | {est(v['net_benefit_pct_points'])} |")
    lines += ['', '**qsort에서는 이득, dijkstra에서는0.0745pp 손해다.** 보호 상태가 같아도 workload의 오류 민감도와 정상 비용이 선택을 바꾼다. Basic TAGE algorithm/update schedule은 그대로이며 보호 결정 timing이 바뀌었다. Helpful D−C<0도 보존했다.', '',
        '이번 손익분기 판단은 해당 가정·λ·program의 B−D와 matched CI다. 한 λ만 평가했으므로 physical λ* 또는 일반화한 cycle-rate break-even threshold를 추정하지 않았다. 실제 update-lane 비용/다른 λ에서 다시 측정해야 한다.', '',
        '### 단일 사건 관측 지연·피해', '',
        '| Program/field | n | Detector delay p95 / max (CPUcycles) | D−C p95 / max (CPUcycles) | Detector censor |', '|---|---:|---:|---:|---:|']
    for t in r['single_event_observed_tails']:
        d=t['detection_delay_CPU_cycles'];v=t['fault_excess_cycles_D_minus_C']
        lines.append(f"| {t['program']}/{t['field']} | {t['normal_exits']} | {d['p95']:.6g} / {d['maximum']:.6g} | {v['p95']:.6g} / {v['maximum']:.6g} | {t['detection_right_censored']} |")
    lines += ['', '20single detector censor0, 최대 관측 delay246.254cycles/D−C20178cycles다. Field/program당5seed p95는 population/worst-case bound가 아니다. 일부 single-condition B−D<0도 보존했다.', '',
        '### 조건부 공간·시간 holdout', '',
        '96회 원본 disjoint trace·고정 source schedule의 matched point estimates다. Group당2seeds×2fixed traces, robust CI/tail 확인은 미완료다. CPUcycles와 같은 노출로 합치지 않는다.', '',
        '| Family/condition | P_ED ΔMPKI | k32 ΔMPKI | k32−P_ED |', '|---|---:|---:|---:|']
    for g in m['groups']:
        cond=g['condition']
        if (cond[0]=='FLYING_TIMING' and cond[1]=='collapse') or (cond[0]=='CERN_FOOTPRINT' and cond[2]=='repeat'):
            v=g['means'];lines.append(f"| {'/'.join(cond)} | {v['P_ED']:.6g} | {v['P_PERIODIC_ED']:.6g} | {v['periodic_minus_ED']:.6g} |")
    lines += ['', '시간/geometry 조건에서 차이의 부호가 바뀔 수 있다. 원 모델 K/offsets·duplicate/time 정책을 유지한 탐색 결과이며 k32의 보편적 우위나 physical rate/layout 증명이 아니다.', '',
        '### 원시자료·재현·실행 상태', '',
        'periodic_policy_selection.lock.json, periodic_extension.lock.json, gem5_periodic_source.lock.json, PERIODIC_CPU_GATE/EVAL.json, PERIODIC_EXTENSION_SUMMARY.json, PERIODIC_MODEL_HOLDOUT/SUMMARY.json 및 모든raw schedule/stats/config/event/repair/native output을 보존했다. Python39tests/CPP369oddbit·speculation/O3 checksum13cases가PASS다. 기존gem5-e3 source/binary와corrected baseline files는 유지했다.', '',
        '초기 C++ test snapshot API 오타와 CPU preflight의 P0 clean 참조phase 차이를 각1회 수정했다. CPU preflight 전체log와 CPP compiler error의 실제tool-output excerpt를 보존했다(CPP초기 full log는 수정compile 때 덮어써 보존하지 못했다). 이를 성공적인 FI run으로 세지 않았다. Fixed CPU evaluation42는 모두 정상 종료했다.', '',
        '재현: setup/build_gem5_periodic.sh → scripts/test_gem5_periodic.py → scripts/run_periodic_cpu.py → scripts/summarize_periodic_extension.py; source-pattern run/summarize는 periodic_model_holdout 관련scripts; tables는 scripts/render_periodic_report.py. 기존 producer를 덮어쓰지 않는다. 실행 전 frozen selection·source/config hashes를 확인한다.']
    output=ROOT/'reports/PERIODIC_EXTENSION_REPORT.ko.md';output.write_text(text+'\n'+'\n'.join(lines)+'\n')
    record={'status':'GENERATED_FROM_AUDITED_COMPLETE_PERIODIC_PILOTS','source_hashes':{p:sha(ROOT/p) for p in ['docs/11_PERIODIC_METHOD.ko.md','reports/PERIODIC_EXTENSION_SUMMARY.json','reports/PERIODIC_MODEL_SUMMARY.json']},'report_sha256':sha(output),'generator_sha256':sha(Path(__file__)),'physical_rate_or_PPA_measured':False}
    (ROOT/'reports/PERIODIC_EXTENSION_REPORT.json').write_text(json.dumps(record,indent=2)+'\n')
    print(record['status'])
if __name__=='__main__':main()
