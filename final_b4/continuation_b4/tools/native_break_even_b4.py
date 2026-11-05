"""Derived threshold only. Native matched-fault B is unmeasured."""
import sys, statistics
sys.dont_write_bytecode = True
import resources as r
ROOT = r.BASE
K = ROOT / 'runtime/continuation_b4'

def derive():
    native = r.load(ROOT / 'reports/NATIVE_REFERENCE6.json')
    assert native['status'] == 'PASS'
    clean = {(x['task']['label'].split('.')[1], x['task']['program']): x['cycles'] for x in native['rows']}
    rows = []
    for cohort in ('DEV', 'EVAL'):
        path = K / 'reports' / (cohort + '_ANALYSIS.json')
        if not path.exists():
            continue
        groups = {}
        for x in r.load(path)['paired_rows']:
            if not x['valid_pair']:
                continue
            A = clean[cohort, x['program']]
            key = x['program'], x['scenario'], x['method']
            groups.setdefault(key, []).append({'owner': x['owner'], 'native_clean_A': A,
                'finite_fault_D': x['D'], 'required_native_fault_slowdown_pct': 100 * (x['D'] / A - 1),
                'finite_common_B_minus_D': x['net_cycles']})
        for (program, scenario, method), owners in sorted(groups.items()):
            rows.append({'cohort': cohort, 'program': program, 'scenario': scenario, 'method': method,
                         'owners': owners, 'mean_required_native_fault_slowdown_pct': statistics.mean(x['required_native_fault_slowdown_pct'] for x in owners)})
    r.put(K / 'reports/NATIVE_BREAK_EVEN_THRESHOLDS.json', {
        'status': 'NEW_DERIVATION_ACTUAL_NATIVE_A_FINITE_D_NOT_MEASURED_NATIVE_FAULT_B',
        'formula': 'Positive native-relative net B_native-D requires native fault slowdown > D/A_native-1.',
        'native_reference': r.ref(ROOT / 'reports/NATIVE_REFERENCE6.json'), 'rows': rows,
        'not_measured_native_protection_win': True})
    print('B4_NATIVE_BREAK_EVEN_DERIVED', len(rows), flush=True)

if __name__ == '__main__':
    derive()
