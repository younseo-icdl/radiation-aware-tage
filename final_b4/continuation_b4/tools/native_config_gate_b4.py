"""Compare actual system configuration; predictor resource changes are explicit."""
import sys, pathlib
sys.dont_write_bytecode = True
import resources as r
ROOT = r.BASE
K = ROOT / 'runtime/continuation_b4'
ALGORITHM = ('histBufferSize', 'initialTCounterValue', 'instShiftAmt',
    'logRatioBiModalHystEntries', 'logTagTableSizes', 'logUResetPeriod', 'maxHist',
    'maxNumAlloc', 'minHist', 'nHistoryTables', 'noSkip', 'numThreads',
    'numUseAltOnNa', 'pathHistBits', 'speculativeHistUpdate', 'tagTableCounterBits',
    'tagTableTagWidths', 'tagTableUBits', 'takenOnlyHistory', 'useAltOnNaBits')

def gate(cohort='DEV'):
    assert cohort in ('DEV', 'EVAL')
    rows = []
    for item in r.load(K / 'reports' / (cohort + '_CLEAN_COMPLETED.json'))['runs']:
        row = r.load(item['path'])
        program = row['program']
        native = ROOT / 'runtime/cpu_trials' / f'NATIVE_REFERENCE.{cohort}.{program}/config.json'
        fresh = pathlib.Path(row['task']['output']) / 'config.json'
        a, b = r.load(native), r.load(fresh)
        predictors = []
        for cfg in (a, b):
            cpu = cfg['system']['cpu']
            predictors.append(cpu['branchPred'].pop('conditionalBranchPred'))
            for proc in cpu['workload']:
                proc.pop('output')
                proc.pop('errout')
        assert a == b, ('UNRELATED_SYSTEM_OR_O3_DIFFERENCE', program, row['method'])
        na, nb = [x['tage'] for x in predictors]
        for key in ALGORITHM:
            assert key in na and key in nb and na[key] == nb[key], ('TAGE_ALGORITHM_PARAMETER_DIFFERENCE', key)
        rows.append({'program': program, 'method': row['method'],
            'native_config': r.ref(native), 'B4_config': r.ref(fresh),
            'algorithm_parameters_checked': {key: na[key] for key in ALGORITHM},
            'declared_exceptions': ['conditional predictor resource/protection/logging parameters',
                                    'process stdout/stderr output directory paths']})
    target = 'NATIVE_B4_SYSTEM_CONFIG_GATE.json' if cohort == 'DEV' else 'NATIVE_B4_EVAL_SYSTEM_CONFIG_GATE.json'
    r.put(K / 'reports' / target, {
        'status': 'PASS_ALL18_' + cohort + '_SYSTEM_O3_CACHE_MEMORY_INPUT_AND_TAGE_PARAMETERS_WITH_DECLARED_EXCEPTIONS',
        'rows': rows, 'does_not_claim_identical_timing_or_wrong_path_interleavings': True,
        'does_not_qualify_binary_semantics_from_config_alone': True, 'no_CPU_reexecution': True})
    print('PASS_NATIVE_B4_ACTUAL_CONFIGS', len(rows), flush=True)

if __name__ == '__main__':
    gate()
