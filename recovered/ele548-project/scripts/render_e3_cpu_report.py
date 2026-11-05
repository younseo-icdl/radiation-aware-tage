#!/usr/bin/env python3
"""Render already audited CPU comparisons; refuse partial or engineering-pilot inference."""
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from summarize_e3_cpu import sha

ROOT = Path(__file__).resolve().parents[1]
SCHEMES = ['P0', 'P_ED', 'P_ECC', 'P_TMR']


def main():
    c = json.loads((ROOT/'configs/e3.cpu.lock.json').read_text())
    summaries = {}
    for phase in ['main', 'latency']:
        summary = json.loads((ROOT/f'reports/E3_CPU_{phase.upper()}_SUMMARY.json').read_text())
        assert summary['status'] in ['PASS_AUDITED_COMPLETE_CPU_PHASE', 'AUDITED_COMPLETE_CPU_PHASE_WITH_FAILURES']
        assert summary['campaign_sha256'] == sha(ROOT/f'reports/E3_CPU_{phase.upper()}.json')
        assert summary['config_sha256'] == sha(ROOT/'configs/e3.cpu.lock.json')
        summaries[phase] = summary
    baseline = json.loads((ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json').read_text())
    lines = ['# 실제 gem5 O3 CPU 성능·오류·가정 latency 비교', '',
        '공식 MiBench 세 프로그램의 같은 native-검증 static ELF/input을 O3에서 실행했다. HW1 branch trace의 ΔMPKI와 구분한다. Cold whole-process 범위이며 libc·입출력·초기 실행을 포함한다. CPU 모델의 결과이며 실제 실리콘 성능/PPA는 아니다.', '',
        f"Main {summaries['main']['attempted_runs']} runs와 latency {summaries['latency']['attempted_runs']} runs를 고정 계획대로 실행했다. 실패 {len(summaries['main']['failures'])+len(summaries['latency']['failures'])}건을 분모에 보존했다. 실행·입력·event·counter·hash audit 결과와 세부 통계는 E3_CPU_MAIN_SUMMARY.json 및 E3_CPU_LATENCY_SUMMARY.json에 있다.", '',
        '## Pristine baseline', '',
        '| Program | CPU cycles | Committed instructions | IPC | Conditional MPKI |',
        '|---|---:|---:|---:|---:|']
    for row in baseline['programs']:
        lines.append(f"| {row['program']} | {row['cycles']} | {row['committed_instructions']} | {row['IPC']:.6g} | {row['conditional_MPKI']:.6g} |")
    lines += ['', '## Primary repeated selected-payload CHARM-6T comparison', '',
        '표는 equal-event λ=10⁻⁶/CPU cycle의 가정 stress 설정이다. Target per-bit/second rate가 아니다. 아래 ideal C=R=0 비교와 실제 경로에 연결한 assumed latency 비교를 별도로 읽는다.', '',
        '| Program | Scheme | Mean cycles | IPC | Conditional MPKI | Total slowdown (%) | Benefit vs faulty P0 (percentage points of pristine) |',
        '|---|---|---:|---:|---:|---:|---:|']

    def primary(summary, scheme, check=0, repair=0, rate=1e-6):
        return next(g for g in summary['groups'] if g['mode'] == 'repeat' and g['profile'] == 'M1_CHARM_6T'
                    and g['population'] == 'selected_payload' and g['normalization'] == 'equal_event'
                    and g['rate'] == rate and g['scheme'] == scheme and g['check'] == check and g['repair'] == repair)

    def value(metrics, name):
        estimate = metrics.get(name)
        return 'NA' if estimate is None else f"{estimate['mean']:.6g}"

    for program in c['programs']:
        for scheme in SCHEMES:
            metrics = primary(summaries['main'], scheme)['program_metrics'][program]
            lines.append('| '+program+' | '+scheme+' | '+' | '.join(value(metrics, name) for name in
                ['cycles', 'IPC', 'conditional_MPKI', 'total_slowdown_pct', 'benefit_pct_points_of_pristine_vs_P0_fault'])+' |')
    lines += ['', '## Assumed latency on actual response/repair path', '',
        '| Scheme | Check cycles | Repair cycles | Clean overhead (%) | Fault loss vs own clean (%) | Total slowdown (%) | Benefit vs faulty P0 (pp) |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for scheme in SCHEMES[1:]:
        for check in c['latency_sensitivity']['check_cycles']:
            for repair in c['latency_sensitivity']['repair_cycles']:
                metrics = primary(summaries['latency'], scheme, check, repair)['metrics']
                lines.append(f'| {scheme} | {check} | {repair} | '+' | '.join(value(metrics, name) for name in
                    ['protection_clean_overhead_pct', 'fault_loss_pct_of_own_clean', 'total_slowdown_pct', 'benefit_pct_points_of_pristine_vs_P0_fault'])+' |')
    lines += ['', '네 조건의 비교 계약: A=P0 clean, B=P0 faulty, C=protected clean, D=protected faulty. Clean overhead=100(C/A−1), fault loss=100(D/C−1), total slowdown=100(D/A−1), net benefit=100(B−D)/A. 따라서 보호법의 정상 비용을 오류 복구의 효과와 섞지 않는다. Mean cycles와 mean IPC는 비선형 관계여서 별도 평균을 보고한다.', '',
        'Timing 계약: '+c['latency_contract']+'. C/R는 RTL에서 얻은 값이 아니다. 같은 clock/CPU/cache 설정을 유지하고 실제 hold·cancel·repair 발생과 CPU cycles를 측정했다. Backend repair와 frontend/backend overlap이 있으므로 repair count×R를 CPU slowdown으로 대체하지 않는다.', '',
        '정확성 gate는 zero-fault full-state/RNG/counter 동등성, signed/raw/folded logical FI, same-tick atomic/input-order, stale rollback/training 억제, 130-actual-commit refill과 queue drain, 추가 bit 노출 및 각 code의 보장 밖 오류를 검증했다. Actual trace/program FI는 normal native answer와 exit를 확인했다. Assertion/timeout/syscall/출력 실패는 masked fault가 아니다.', '',
        '반복 clock은 독립 Poisson cycle 좌표를 integer Tick로 올림하며 같은 tick의 distinct events를 보존한다. Injection priority49가 CPU Tick50보다 앞선다. Arrival clock은 predictor hold 동안에도 계속된다. Normal exit 이후 사건은 right-censor하고 4×pristine model stop이나 wall timeout은 실패로 기록한다. Slow designs의 더 긴 오류 노출도 결과에 포함한다.', '',
        'Statistical unit은 program 내 matched seed다. Bootstrap 2000회, 세 고정 program의 동일 가중 mean이며 unseen-workload 모집단 또는 물리 flux 신뢰구간이 아니다. Helpful/zero를 포함했다. Failure는 attempted denominator와 program별 Wilson CI에 남기며, 수치 평균은 normal exit에 조건화하고 paired benefit은 두 설계의 normal exit pair에 조건화한다.', '',
        '선택 payload / paired base-full / storage-scaled full을 별도로 평가했다. Storage-scaled는 실제 추가 저장 bits의 비례 노출 가설이며 area ratio 또는 측정 cross section이 아니다. In-flight epoch/BranchInfo/transport/architectural state/BTB/RAS/shared SET 등 explicit exclusions는 config와 E4 functional handoff에 있다. 전체 CPU radiation qualification을 주장하지 않는다.', '',
        'E4는 유예했다. 같은 기능·interface·library/PVT/clock/load·실제 activity로 RTL timing/PPA를 측정하고 이번 C/R 가정을 교체한 뒤 최종 비용 결론을 통합해야 한다.', '',
        '재현: scripts/run_e3_cpu.py --phase pilot/main/latency; scripts/summarize_e3_cpu.py --phase main/latency; scripts/render_e3_cpu_report.py. Source pin·binary·scope·config·schedule·각 run raw output과 summary hashes를 함께 보존한다.']
    (ROOT/'reports/E3_CPU_REPORT.ko.md').write_text('\n'.join(lines)+'\n')
    destination = ROOT/'reports/e3_cpu/figures'
    destination.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    x = np.arange(4)
    for ax, rate in zip(axes, c['base_event_rates_per_CPU_cycle']):
        estimates = [primary(summaries['main'], scheme, rate=rate)['metrics']['total_slowdown_pct'] for scheme in SCHEMES]
        if any(e is None or e['bootstrap95CI'] is None for e in estimates):
            ax.text(.5, .5, 'Insufficient normal-exit seed data', ha='center')
            continue
        means = np.array([e['mean'] for e in estimates])
        ci = np.array([e['bootstrap95CI'] for e in estimates])
        ax.bar(x, means, yerr=np.maximum(0, np.stack([means-ci[:, 0], ci[:, 1]-means])), capsize=4)
        ax.set_xticks(x, SCHEMES)
        ax.set_ylabel('Total CPU cycle slowdown (%)')
        ax.set_title(f'CHARM 6T, assumed {rate:g} events/cycle')
        ax.axhline(0, color='gray', lw=.6)
    fig.suptitle('Selected payload; ideal response latency; equal fixed-program weights')
    fig.tight_layout()
    for ext in ['png', 'pdf']:
        fig.savefig(destination/f'cpu_fault_slowdown.{ext}', dpi=180)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, scheme in zip(axes, SCHEMES[1:]):
        for repair in c['latency_sensitivity']['repair_cycles']:
            estimates = [primary(summaries['latency'], scheme, check, repair)['metrics']['total_slowdown_pct']
                         for check in c['latency_sensitivity']['check_cycles']]
            if any(e is None or e['bootstrap95CI'] is None for e in estimates):
                continue
            means = np.array([e['mean'] for e in estimates])
            ci = np.array([e['bootstrap95CI'] for e in estimates])
            ax.errorbar(c['latency_sensitivity']['check_cycles'], means,
                yerr=np.maximum(0, np.stack([means-ci[:, 0], ci[:, 1]-means])), label=f'R={repair}', marker='o', capsize=3)
        ax.set_title(scheme)
        ax.set_xlabel('Assumed check cycles C')
        ax.set_ylabel('Total CPU cycle slowdown (%)')
        ax.legend()
    fig.suptitle('Actual response holds and serial repair batches; assumed C/R, no RTL timing')
    fig.tight_layout()
    for ext in ['png', 'pdf']:
        fig.savefig(destination/f'cpu_assumed_latency.{ext}', dpi=180)
    plt.close(fig)
    from export_e4_software_contract import main as export_activity
    export_activity()
    from render_software_integration import main as integrate_software
    integrate_software()
    from audit_software_completion import main as audit_completion
    audit_completion()
    print('PASS complete CPU report, scientific figures and audited activity proxies')


if __name__ == '__main__':
    main()
