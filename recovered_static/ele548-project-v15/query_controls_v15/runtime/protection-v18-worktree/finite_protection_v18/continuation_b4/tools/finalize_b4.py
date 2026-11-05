"""Audit closed actual B4 evidence. No simulation, retries, or invented cells."""
import sys, pathlib, json, datetime
sys.dont_write_bytecode = True
import resources as r
ROOT = r.BASE
K = ROOT / 'runtime/continuation_b4'

def audit():
    rows, checked = [], 0
    for marker in sorted((ROOT / 'runtime/run_starts').glob('*.json')):
        task = r.load(marker)
        record = pathlib.Path(task['output']) / 'EXECUTION.json'
        assert record.exists(), ('ACTIVE_RECORD_NOT_TERMINAL', task['label'])
        row = r.load(record)
        for name, digest in row.get('hashes', {}).items():
            assert r.sha(record.parent / name) == digest, ('RAW_CHANGED', str(record.parent / name))
            checked += 1
        rows.append({'label': task['label'], 'phase': task['phase'], 'status': row['status'],
                     'failure': row.get('failure'), 'execution': r.ref(record)})
    producer = r.load(ROOT / 'reports/PRODUCER_B4.lock.json')
    for item in [producer['binary'], producer['config'], producer['observer']] + producer['actual_dependencies']:
        assert r.sha(item['path']) == item['sha256'], ('B4_COMPILED_DEPENDENCY_DRIFT', item['path'])
    for item in r.load(producer['source_lock']['path'])['files']:
        assert r.sha(item['path']) == item['sha256'], ('B4_SOURCE_DRIFT', item['path'])
    old = r.load(ROOT / 'reports/PRESERVED_BASELINE.lock.json')
    assert r.sha(old['current_binary']['path']) == old['current_binary']['sha256']
    for cohort in ('DEV', 'EVAL'):
        for item in r.load(K / 'reports/COHORT_INPUTS.lock.json')[cohort]:
            for key in ('input', 'program_binary', 'expected_stdout', 'payload'):
                if key in item:
                    assert r.sha(item[key]['path']) == item[key]['sha256'], ('INPUT_DRIFT', cohort, item['program'], key)
    if (K / 'reports/DEV_CLEAN_COMPLETED.json').exists() and (ROOT / 'reports/NATIVE_REFERENCE6.json').exists() and r.load(ROOT / 'reports/NATIVE_REFERENCE6.json')['status'] == 'PASS' and not (K / 'reports/NATIVE_B4_SYSTEM_CONFIG_GATE.json').exists():
        import native_config_gate_b4
        native_config_gate_b4.gate()
    if (K / 'reports/EVAL_CLEAN_COMPLETED.json').exists() and (ROOT / 'reports/NATIVE_REFERENCE6.json').exists() and r.load(ROOT / 'reports/NATIVE_REFERENCE6.json')['status'] == 'PASS' and not (K / 'reports/NATIVE_B4_EVAL_SYSTEM_CONFIG_GATE.json').exists():
        import native_config_gate_b4
        native_config_gate_b4.gate('EVAL')
    complete = (K / 'reports/FINITE_MATRIX_COMPLETED.json').exists()
    if complete:
        for name, count in (('DEV_CLEAN', 18), ('DEV_FAULT', 102), ('EVAL_CLEAN', 18), ('EVAL_FAULT', 408)):
            phase = r.load(K / 'reports' / (name + '_COMPLETED.json'))
            assert phase['status'] == 'PASS' and phase['actual_runs'] == count
        for name, count in (('DEV_SERIAL', 18), ('DEV_L2', 6)):
            phase = r.load(ROOT / 'reports' / (name + '_COMPLETED.json'))
            assert phase['status'] == 'PASS' and phase['actual_runs'] == count
        assert r.load(ROOT / 'reports/NATIVE_REFERENCE6.json')['status'] == 'PASS'
        assert r.load(K / 'reports/EVAL_ANALYSIS.json')['attempted_faults'] == 408
    report = {'status': 'PASS_COMPLETED_B4_MATRIX_AUDIT_NOT_HARDWARE_QUALIFICATION' if complete else 'INCOMPLETE_OR_STOPPED_B4_ACTUAL_EVIDENCE_AUDITED',
              'at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'actual_new_CPU': len(rows),
              'records': rows, 'raw_hashes_checked': checked, 'producer': r.ref(ROOT / 'reports/PRODUCER_B4.lock.json'),
              'B2_protection_qualification_revoked': r.ref(ROOT / 'reports/B2_PROTECTION_QUALIFICATION_REVOKED.json'), 'B3_repeated_fault_gate_failed': r.ref(ROOT / 'reports/B3_REPEATED_FAULT_GATE_FAILURE.json'),
              'resources': r.snapshot(), 'original_results_preserved': True, 'no_RTL_PPA_or_hardware_qualification': True}
    r.put(K / 'reports/ACTUAL_TERMINAL_AUDIT.json', report)
    lines = ['# v18 B4 실제 실행 보고서', '', '상태: ' + report['status'], '',
             f"DONE: 실제 새 CPU {len(rows)}회, raw SHA {checked}개와 B4 source/config/ELF/compiled dependencies 및 기존 ELF·입력·정답 hash를 검증했다. 이전 실패·진단과 B2 정상 대조는 별도 producer의 원본으로 보존했다.", '',
             'B4는 RMW raw/path post-image를 유지하고 실제 retirement에서 resolved outcome을 finite ingress에 한 번 등록한다. B3 delayed-callback overflow를 재현·보존했다. 최신 C++8gate/8,650 source-phase 사례 및 추가64retire/105backpressure cycle·metadata112SBU가 통과했다. 새 O3 checksum6/overlap6/mid-DUE6이 통과했으며 이전 B3 post-RMW4를 새 B4 실행으로 세지 않는다.']
    if complete:
        ev = r.load(K / 'reports/EVAL_ANALYSIS.json')
        lines += ['', 'DONE: 새 B4 개발 fault 102건·독립 fault 408건 및 정상 36건이 종료됐다. Native 정상 6건과 이전 B2 serial 18건/L2 6건은 각각 실제 producer를 구분한다. B2 대조를 B4의 새 측정으로 세지 않았다.', '',
                  '| 프로그램 | 방법 | clean cycles | IPC | 실제 consume/source cycle | 최대 lookup |',
                  '|---|---|---:|---:|---:|---:|']
        for x in ev['clean']:
            lines.append(f"| {x['program']} | {x['method']} | {x['cycles']} | {x['IPC']:.6f} | {x['consumed_per_source_cycle']:.6f} | {x['max_lookup_pending']} |")
        lines += ['', '| 프로그램 | 조건 | 방법 | valid/observed owners | mean B−D cycles | bootstrap95% cycles | 순이득 %A |',
                  '|---|---|---|---:|---:|---|---:|']
        for x in ev['paired_summaries']:
            if x['method'] == 'P0':
                continue
            ci = x['bootstrap95_cycles']
            interval = '미산출' if ci is None else f'[{ci[0]:.1f}, {ci[1]:.1f}]'
            lines.append(f"| {x['program']} | {x['scenario']} | {x['method']} | {x['valid_pairs']}/{x['observed_owners']} | {x['mean_B_minus_D']} | {interval} | {x['mean_net_pct_A']} |")
        lines += ['', '표본은 프로그램·조건별 독립 owner 8개다. 공유 A/C나 보호법 반복을 추가 표본으로 세지 않는다. Paired bootstrap CI는 n=8 탐색적 추정이며 exact-sign/Holm·음수·0·helpful 사건·완전 pair ID·실패 분모는 EVAL_ANALYSIS.json에 남겼다.', '',
                  'A/B/C/D 해석: C−A는 정상 유지 비용, D−C는 보호 상태의 오류 후 총 cycle 증가분이다. 후자는 남은 prediction 피해와 repair/relearn 비용·backpressure를 함께 포함한다. JSON의 residual_damage 이름을 순수 기능 피해만으로 읽지 않는다. B−D=(B−A)−(C−A)−(D−C)이며 overlap 가능한 check/repair/stall 동작 횟수만으로 D−C를 정확히 분해하지 않는다.']
    else:
        lines += ['', 'NOT DONE: 전체 matrix가 완료되지 않았다. 실행하지 않은 cycles/CI는 생성하지 않았다. 고정 plan·STOP 파일과 실제 개별 EXECUTION에서 남은 조건을 확인한다.']
    lines += ['', 'VERIFIED ASSUMPTIONS: 공통 check/encode/provider 각 1 stage·유한 lane/queue/ports는 CPU resource 모델 가정이다. P0도 공통 no-op check/encode 경로를 통과하므로 C−A가 작아도 실제 ECC/TMR 비용이 0이라는 뜻이 아니다. Native 정상 6건은 참고점이며 matched-native fault B−D를 측정한 것은 아니다.', '',
              '분리 범위: 같은 L의 serial/early 비교는 unconditional next-PC가 알려진 경우의 실제 중첩·single-pending 대기를 비교한다. Conditional next-PC/history·source ordering 의존성은 남는다. L1/L2는 source history/fold stage 민감도이며 provider/table LUT는 1로 고정되어 LUT 자체 latency 효과는 미확정이다. Stall 합계를 정확한 CPI 인과 분해로 해석하지 않는다.', '',
              '오류 범위: SOURCE raw130 조건부 공격과 WHOLE 추가 storage 노출은 분리한다. Added uncoded encoder latch·retention·CPU-owned association 제외·protection epoch의 full CPU 검증 한계를 manifest/model card에 남긴다. Decoder corrected는 동작 횟수이며 golden 정답 복구 증명이 아니다.', '',
              'BLOCKERS/NEXT: 실제 STOP·예산 한계가 있으면 미시작 고정 조건과 필요한 추가 실행량을 보고한다. 완료했다면 프로그램별 순이득·실패·비용 Pareto를 검토한다. RTL/Cadence/SPICE/TCAD·실측 PPA와 하드웨어 우위는 아직 검증하지 않았다.']
    (K / 'reports/ACTUAL_TERMINAL_REPORT.ko.md').write_text('\n'.join(lines) + '\n')
    if (K / 'reports/DEV_CLEAN_COMPLETED.json').exists() and (ROOT / 'reports/NATIVE_REFERENCE6.json').exists() and r.load(ROOT / 'reports/NATIVE_REFERENCE6.json')['status'] == 'PASS':
        import cost_controls_b4
        cost_controls_b4.compare()
    print(report['status'], len(rows), checked, flush=True)

if __name__ == '__main__':
    audit()
