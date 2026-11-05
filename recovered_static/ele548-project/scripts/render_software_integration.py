#!/usr/bin/env python3
"""Link model sensitivity to actual CPU cost; pending data cannot become final results."""
import argparse
import json
from pathlib import Path
from summarize_e3_cpu import sha

ROOT = Path(__file__).resolve().parents[1]
SCHEMES = ['P0', 'P_ED', 'P_ECC', 'P_TMR']


def load_summary(name, config):
    path = ROOT/f'reports/{name}_SUMMARY.json'
    data = json.loads(path.read_text())
    assert data['status'].startswith('PASS')
    assert data['config_sha256'] == sha(ROOT/f'configs/{config}.lock.json')
    return data


def interval(entry):
    for key in ['matched_trial_bootstrap95CI', 'matched_trial_bootstrap_95CI',
                'trial_bootstrap_95CI', 'bootstrap95CI']:
        if key in entry:
            ci = entry[key]
            if ci is None:
                return f"{entry['mean']:.6g} (CI unavailable)"
            return f"{entry['mean']:.6g} [{ci[0]:.6g}, {ci[1]:.6g}]"
    raise KeyError('confidence interval missing')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-pending-cpu', action='store_true')
    args = parser.parse_args()
    e1 = load_summary('E1', 'e1.design')
    e2 = load_summary('E2', 'e2.holdout')
    flying = load_summary('FLYING_TIMING', 'flying_timing')
    cern = load_summary('CERN_FOOTPRINT', 'cern_footprint')
    assert e1['namespace_correction']['rng_namespace_version'] == 2
    assert e1['namespace_correction']['frozen_scope_preserved']
    scope = json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
    assert e1['selection']['scope_sha256'] == e2['scope_sha256'] == sha(ROOT/'sources/protection_scope.lock.json')
    cpu = {}
    for phase in ['main', 'latency']:
        path = ROOT/f'reports/E3_CPU_{phase.upper()}_SUMMARY.json'
        if path.exists():
            data = json.loads(path.read_text())
            assert data['status'] in ['PASS_AUDITED_COMPLETE_CPU_PHASE', 'AUDITED_COMPLETE_CPU_PHASE_WITH_FAILURES']
            assert data['campaign_sha256'] == sha(ROOT/f'reports/E3_CPU_{phase.upper()}.json')
            assert data['config_sha256'] == sha(ROOT/'configs/e3.cpu.lock.json')
            cpu[phase] = data
    complete = len(cpu) == 2
    reviewed = False
    review_path = ROOT/'reports/SOFTWARE_FINAL_REVIEW.json'
    if complete and review_path.exists():
        review = json.loads(review_path.read_text())
        assert review['status'] == 'PASS_REVIEWED_CADENCE_PRE_SOFTWARE_SCOPE'
        for path, digest in review['reviewed_evidence_sha256'].items():
            assert sha(ROOT/path) == digest, f'final review is stale: {path}'
        reviewed = True
    if not args.allow_pending_cpu:
        assert complete, 'Both audited CPU phases required; no final report from pilot/partial runs'
        assert (ROOT/'reports/E3_CPU_REPORT.ko.md').exists()
    lines = ['# Cadence 전 소프트웨어 통합 결과', '',
        '**상태: '+('Cadence 전 소프트웨어 범위 완료·최종 검토 PASS. 검토 기록: SOFTWARE_FINAL_REVIEW.json.' if reviewed else
                       'CPU main/latency 완료 결과 포함 — 최종 evidence review 필요.' if complete else
                       'C++ 모델 결과 완료, CPU main/latency 진행 중. 전체 목표 미완료.')+'**', '',
        '연구 질문은 TAGE 상태의 역할과 회복 경로, 관측된 오류 크기·공간·시간 패턴이 같은 S*의 보호 선택에 어떤 차이를 만드는지다. Actual CPU overhead는 gem5로 측정하고 실제 구현 비용/PPA는 이후 같은 PDK 조건에서 측정한다. Source facts와 선언한 stress 가정, 구현 결과를 구분한다.', '',
        '## 상태별 single-event와 동결 범위', '',
        'HW1 CBP/SPEC2006 유래 6개 trace의 design5760과 warmup600을 namespace v2로 실행했다. 동일 post100k conditional horizon/original instruction denominator, design/holdout disjoint 구간과 seed를 유지했다. 기존 S* hash를 보존하는 independent corrected-design confirmation이며 holdout으로 다시 선택하지 않았다.', '',
        '| Field | Bits | Mean net extra misses | ΔMPKI | Bit-weighted ΔMPKI (95% CI) | End-state unequal fraction |',
        '|---|---:|---:|---:|---:|---:|']
    for item in e1['models']:
        if item['model'] != 'M0':
            continue
        lo, hi = item['bit_weighted_delta_MPKI_CI95']
        lines.append(f"| {item['field']} | {item['bits']} | {item['mean_net_extra_misses']:.6g} | {item['mean_delta_MPKI']:.6g} | {item['bit_weighted_delta_MPKI']:.6g} [{lo:.6g}, {hi:.6g}] | {item['not_equal_at_H_fraction']:.6g} |")
    lines += ['', f"S*={','.join(scope['selected_fields'])}, {scope['payload_bits']} bits/{scope['payload_word_count']} natural words. Raw history는 이후 folded index/tag state와 allocation/training에 영향을 주고 folded state는 여러 table의 lookup 선택에 직접 관여한다. 회복은 원 upset bit가 없어졌는지뿐 아니라 downstream residual state와 prediction을 함께 본다. 마지막 mismatch를 영구 회복 시각으로 해석하지 않는다.", '',
        '## 같은 S*의 SBU/CHARM 반복 주입', '',
        '아래는 selected-payload λ_reference=10⁻³/conditional branch다. P0와 세 기본 복구법을 같은 payload 사건에 대응시킨 조건이다. Added-cell exposure는 별도 paired-base/full-storage 조건에 포함했다. Event rate는 source-calibrated target per-bit/second rate가 아니다.', '',
        '| Model/normalization | P0 ΔMPKI | Parity ΔMPKI | SECDED ΔMPKI | TMR ΔMPKI |',
        '|---|---:|---:|---:|---:|']
    for group in e2['groups']:
        if group['mode'] != 'repeat' or group['population'] != 'selected_payload' or group['field'] != 6:
            continue
        if group['base_reference_rate_per_conditional'] != .001:
            continue
        lines.append('| '+group['model']+' | '+' | '.join(interval(group['schemes'][s]['metrics']['delta_MPKI']) for s in SCHEMES)+' |')
    lines += ['', 'CHARM L06 PDF p13 TableII의 6T K weights205:9, 8T142:5를 구분했다. Same-event λ와 same-expected-flip λ/E[K]를 혼합하지 않는다. SECDED single writeback/DUE fallback, parity skip/relearn, TMR vote/repair가 실제 동작한다. Parity even corruption, SECDED>=3 missed/miscorrection, TMR 동일 bit의 두 사본 오류 등 보장 밖 경우는 correctness gate와 별도 exposure 조건에서 보존한다.', '',
        '## 시간 순서와 공간 패턴', '',
        'Flying Laptop: 원본2129/2055/74 audit. 같은 collapsed2055 SBU detections를 동일 branch exposure로 압축한 observed/permuted/fixed-N Poisson 가설을 비교했다. Target particle inter-arrival이나 MCU K를 추정한 데이터가 아니다.', '',
        '| Scheme | Observed−fixed-N Poisson ΔMPKI (95% CI) |', '|---|---:|']
    for scheme in SCHEMES:
        group = next(g for g in flying['groups'] if g['policy'] == 'collapse' and g['profile'] == 'SBU'
                     and g['timing'] == 'observed_detection_gaps' and g['scheme'] == scheme)
        lines.append('| '+scheme+' | '+interval(group['delta_MPKI_difference_from_fixed_N_Poisson'])+' |')
    lines += ['', '시간 압축·branch-bin projection에서 검사 사이에 여러 SBU가 쌓이면 DUE/reset/refill 부담이 바뀐다. 이것을 physical MCU로 재분류하지 않는다. Duplicate preserve는 extra hypothetical arrivals 정책 민감도이고 duplicate rows를 MCU size로 쓰지 않는다.', '',
        'CERN: 공급자 세파일 MD5/full parse와 standalone 2014/2015 및 REDW 2020 원문 검토를 완료했다. L11 p6은 singleton SBU와 K≥2 Type A를 구분한다. Recorded K≥2 catalog에 조건화하고 source coordinate/K를 모두 유지했다. 파일별 grouping thresholds·singleton completeness와 target physical layout/pitch는 식별하지 못했다. 원문 사례의 임계값을 이 65nm 자료의 생성 설정으로 옮기지 않는다. 두 가상 logical word 배치와 dispersed same-K 대조는 physical placement 측정이 아니다. 현재 근거는 CERN_METHOD_REVIEW.ko.md와 cern_method_review_addendum_20261013.json에 있고 실행 당시 model card bytes는 보존했다.', '',
        '| Condition | Scheme | Interleaved−contiguous ΔMPKI, repeat equal-event (95% CI) |', '|---|---|---:|']
    for group in cern['groups']:
        if group['mode'] == 'repeat' and group['normalization'] == 'equal_event' and group['mapping'] == 'word_interleaved':
            lines.append('| '+group['file']+' | '+group['scheme']+' | '+interval(group['difference_from_word_contiguous'])+' |')
    lines += ['', '동일 K에서도 codeword collision이 바뀌어 검출/정정/fallback 부담이 달라질 수 있다. CI가0을 포함하는 비교는 mean 순서만으로 우위를 확정하지 않는다. Payload-only TMR는 두 건강한 사본을 유지하므로 이 조건의0 손실로 physical replica isolation 또는 전체 CPU 내성을 증명하지 않는다.', '',
        '## 실제 CPU 성능과 검사·복구 비용', '']
    if not complete:
        lines += ['**NOT DONE:** representative main4092 및 latency687의 완료·CI·실패율·CPU 그림. Pilot이나 C++ ΔMPKI를 이 결과로 대체하지 않는다. E3_CPU_REPORT.ko.md는 두 audited phases가 완료된 뒤 작성한다.']
    else:
        lines += ['공식 MiBench qsort/dijkstra/SHA-1의 같은 native-검증 ELF/input을 cold whole-process O3에서 실행했다. 세 program을 동일 가중하고 matched trial bootstrap2000을 사용했다. Actual cycles/IPC/committed conditional MPKI·hold/stall·failure 수치는 E3_CPU_REPORT.ko.md와 각phase summary에 있다. HW1 trace 결과와 실제 SPEC CPU execution/공식 점수로 혼동하지 않는다.', '',
            '| Scheme | Ideal C=R=0 total slowdown (%) | C1/R1 total slowdown (%) | C4/R4 total slowdown (%) |', '|---|---:|---:|---:|']
        def select(phase, scheme, check=0, repair=0):
            return next(g for g in cpu[phase]['groups'] if g['mode'] == 'repeat' and g['profile'] == 'M1_CHARM_6T'
                        and g['population'] == 'selected_payload' and g['normalization'] == 'equal_event'
                        and g['rate'] == 1e-6 and g['scheme'] == scheme and g['check'] == check and g['repair'] == repair)
        for scheme in SCHEMES:
            # Latency phase carries ideal references with the very same trial
            # owners; do not mix independent main seeds into this comparison.
            a = select('latency', scheme)['metrics']['total_slowdown_pct']
            entries = [interval(a) if a else 'NA']
            if scheme == 'P0':
                entries += ['P0 reference C=R=0', 'P0 reference C=R=0']
            else:
                for check, repair in [(1, 1), (4, 4)]:
                    value = select('latency', scheme, check, repair)['metrics']['total_slowdown_pct']
                    entries.append(interval(value) if value else 'NA')
            lines.append('| '+scheme+' | '+' | '.join(entries)+' |')
        lines += ['', '위 latency 표의 ideal references와 C/R 조건은 같은 latency-phase trial owners를 사용한다. A=P0 clean, B=P0 faulty, C=protected clean, D=protected faulty로 overhead·fault loss·net benefit을 나누어 읽는다. 일부 실패가 있으면 분모에 남기고 numeric mean은 normal-exit 조건부라고 표시한다. Ideal correction 이득이 있어도 검사 overhead가 포함되면 net CPU 이득이 달라질 수 있다. 실제 C/R를 측정하지 않았으므로 구현 비용의 최적 보호법을 확정하지 않는다.']
    lines += ['', '## 재현·인계·한계', '',
        'Source/config/binary/seed/schedule/raw logs 및 namespace v1 archive를 보존했다. scripts/audit_software_completion.py는 원본 자료와 raw C++/CPU 수치·config/event를 대조하고 미완료 phase를 분리한다. CI는 고정 workload/source/선언한 가정에 조건화하며 physical flux/grouping/PDK uncertainty 또는 미관측 workload 일반화를 포괄하지 않는다. C++ lambda는 conditional-branch 단위, CPU lambda는 cycle 단위이고 workloads/관측창도 다르다. 두 표를 같은 물리 노출 또는 수치 변환 관계로 합치지 않는다.', '',
        'E4 인계: sources/e4_software_interface_contract.json과 E4_SOFTWARE_FUNCTIONAL_HANDOFF.ko.md. Logical operation count는 actual bit-toggle/VCD/PDK energy가 아니다. 여러 callback의 same-Tick atomic software semantics에는 RTL ports/arbitration/throughput 검증이 추가로 필요하다. 동일 function/storage/interface/library/PVT/clock/load와 actual switching으로 Cadence 비용을 측정하고 measured latency를 E3에 반영해야 최종 비용 결론을 낼 수 있다.', '',
        'TCAD/Geant4/mission FIT/TAGE-SC-L과 Cadence를 실행하지 않았다. 기본 세 보호법을 다른 방법으로 대체하지 않는다. 현재 software 진행에 사용자 추가 SPEC 설치·파일·승인은 필요하지 않다.']
    output = ROOT/'reports/SOFTWARE_INTEGRATION_REPORT.ko.md'
    output.write_text('\n'.join(lines)+'\n')
    sources = ['E1', 'E2', 'FLYING_TIMING', 'CERN_FOOTPRINT']
    hashes = {f'reports/{name}_SUMMARY.json': sha(ROOT/f'reports/{name}_SUMMARY.json') for name in sources}
    hashes.update({f'reports/E3_CPU_{phase.upper()}_SUMMARY.json': sha(ROOT/f'reports/E3_CPU_{phase.upper()}_SUMMARY.json') for phase in cpu})
    hashes.update({path: sha(ROOT/path) for path in [
        'sources/cern_methods.lock.json', 'data/curated/cern_method_review_addendum_20261013.json',
        'reports/CERN_METHOD_REVIEW.ko.md']})
    status = {'status': 'PASS_REVIEWED_CADENCE_PRE_SOFTWARE_INTEGRATION' if reviewed else
                       'GENERATED_FULL_SOFTWARE_INTEGRATION_PENDING_FINAL_REVIEW' if complete else 'DRAFT_CPP_COMPLETE_CPU_PENDING',
        'source_summary_hashes': hashes, 'report_sha256': sha(output), 'generator_sha256': sha(Path(__file__)),
        'CPU_main_latency_complete': complete, 'final_evidence_review_complete': reviewed, 'actual_RTL_PPA_measured': False}
    if reviewed:
        status['final_review_sha256'] = sha(review_path)
    (ROOT/'reports/SOFTWARE_INTEGRATION_REPORT.json').write_text(json.dumps(status, indent=2)+'\n')
    print(json.dumps({'status': status['status'], 'report': str(output.relative_to(ROOT))}))


if __name__ == '__main__':
    main()
