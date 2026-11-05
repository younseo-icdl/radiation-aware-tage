"""Measured normal controls, explicitly retaining their producer identities."""
import sys, pathlib
sys.dont_write_bytecode = True
import resources as r
ROOT = r.BASE
K = ROOT / 'runtime/continuation_b3'

def compare():
    native = r.load(ROOT / 'reports/NATIVE_REFERENCE6.json')
    assert native['status'] == 'PASS'
    nc = {x['task']['program']: x for x in native['rows'] if x['task']['label'].split('.')[1] == 'DEV'}
    report = {'status': 'NEW_DERIVATION_FROM_ACTUAL_B3_NORMAL_AND_SEPARATELY_LABELLED_B2_CONTROLS',
              'rows': [], 'B3_normal': r.ref(K / 'reports/DEV_CLEAN_COMPLETED.json'),
              'B2_serial': r.ref(ROOT / 'reports/DEV_SERIAL_COMPLETED.json'),
              'B2_sourceL2': r.ref(ROOT / 'reports/DEV_L2_COMPLETED.json'),
              'native_reference': r.ref(ROOT / 'reports/NATIVE_REFERENCE6.json'),
              'limitations': ['B2 controls are prior producer measurements; fresh B3 normal equality is tested separately.',
                'Same-L serial/early contrast changes frontend overlap with identical source/update/protection resources.',
                'L2 adds a source history/fold stage; provider/table LUT remains one cycle.',
                'P0/Direct include common no-op check/encode slots. Native overhead is measured separately.',
                'Stall attempts overlap and are not an exact CPI causal decomposition.',
                'Native normal reference has no matched native fault B in this matrix.']}
    for item in r.load(K / 'reports/DEV_CLEAN_COMPLETED.json')['runs']:
        p = pathlib.Path(item['path'])
        assert r.sha(p) == item['sha256']
        x = r.load(p)
        program, method = x['program'], x['method']
        old = ROOT / 'runtime/cpu_trials'
        before = r.load(old / f'DEV_CLEAN.{program}.{method}/EXECUTION.json')
        serial = r.load(old / f'DEV_SERIAL.{program}.{method}/EXECUTION.json')
        assert x['cycles'] == before['cycles'] and x['simInsts'] == before['simInsts']
        s = x['program_exit_seu']
        row = {'program': program, 'method': method,
            'B3_pipeline_L1_cycles': x['cycles'], 'B3_IPC': x['IPC'],
            'B2_serial_sameL_cycles': serial['cycles'], 'native_clean_cycles': nc[program]['cycles'],
            'pipeline_vs_B2_serial_cycles_pct': 100 * (x['cycles'] / serial['cycles'] - 1),
            'pipeline_vs_native_clean_cycles_pct': 100 * (x['cycles'] / nc[program]['cycles'] - 1),
            'actual_accepted_per_source_cycle': s['lookup_accepted'] / s['source_cycles'],
            'actual_consumed_per_source_cycle': s['lookup_consumed'] / s['source_cycles'],
            'max_lookup_pending': s['max_lookup_pending'], 'max_source_pending': s['max_source_pending'],
            'normal_checks': s['protection_checks'], 'normal_encodes': s['protection_encodes'],
            'stall_attempts_not_CPI_decomposition': {k: v for k, v in s.items() if 'stall' in k or 'wait' in k or 'hold' in k},
            'B3_execution': r.ref(p), 'B2_serial_execution': r.ref(old / f'DEV_SERIAL.{program}.{method}/EXECUTION.json')}
        l2 = old / f'DEV_L2.{program}.{method}/EXECUTION.json'
        if l2.exists():
            d = r.load(l2)
            row['B2_source_L2_cycles'] = d['cycles']
            row['sourceL2_vs_B3_L1_cycles_pct'] = 100 * (d['cycles'] / x['cycles'] - 1)
            row['B2_L2_execution'] = r.ref(l2)
        report['rows'].append(row)
    target = K / 'reports/NORMAL_COST_CONTROLS.json'
    if target.exists():
        assert r.load(target) == report, 'OBSERVED_NORMAL_REPORT_CHANGED'
    else:
        r.put(target, report)
    lines = ['# 정상 CPU 비용과 중첩 대조', '',
             'B3 정상 측정과 보존된 B2 serial/L2 측정을 구분한다. 모든 B3 정상 cycles/simInsts는 B2 정상 값과 실제 비교했다. Native는 별도 원래 producer의 정상 참고점이다.', '',
             '| 프로그램 | 방법 | B3 cycles | IPC | serial 대비 cycles % | native 대비 cycles % | consume/cycle | max outstanding |',
             '|---|---|---:|---:|---:|---:|---:|---:|']
    for x in report['rows']:
        lines.append(f"| {x['program']} | {x['method']} | {x['B3_pipeline_L1_cycles']} | {x['B3_IPC']:.6f} | {x['pipeline_vs_B2_serial_cycles_pct']:.4f} | {x['pipeline_vs_native_clean_cycles_pct']:.4f} | {x['actual_consumed_per_source_cycle']:.6f} | {x['max_lookup_pending']} |")
    lines += ['', '모든 보호법의 검사/encode stage-fit은 모델 가정이다. 작은 C−A를 실제 PPA 비용 0으로 해석하지 않는다. Source L1/L2와 provider/table LUT1을 구분하며 next-PC/history 의존성의 정확한 CPI 기여는 미확정이다. 원래 native의 matched-fault B가 없어 절대 native-relative 보호 순이득도 이번 matrix만으로 측정하지 못했다.']
    text = '\n'.join(lines) + '\n'
    target = K / 'reports/NORMAL_COST_CONTROLS.ko.md'
    if target.exists():
        assert target.read_text() == text, 'OBSERVED_NORMAL_MD_CHANGED'
    else:
        with target.open('x') as stream:
            stream.write(text)
    print('B3_NORMAL_COST_CONTROLS', len(report['rows']), flush=True)

if __name__ == '__main__':
    compare()
