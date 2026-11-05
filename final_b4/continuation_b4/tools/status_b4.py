"""Read-only shared ledger and B4 phase status, including retained failures."""
import sys, pathlib, json, collections, datetime
sys.dont_write_bytecode = True
import resources as r
ROOT = r.BASE
K = ROOT / 'runtime/continuation_b4'

def snapshot():
    counts = collections.Counter()
    active, failures = [], []
    for marker in sorted((ROOT / 'runtime/run_starts').glob('*.json')):
        task = r.load(marker)
        record = pathlib.Path(task['output']) / 'EXECUTION.json'
        if not record.exists():
            active.append({'label': task['label'], 'output': task['output'], 'started': task['started']})
            continue
        row = r.load(record)
        counts[task['phase'], row['status']] += 1
        if row['status'].startswith('FAIL'):
            failures.append({'label': task['label'], 'failure': row.get('failure'), 'execution': r.ref(record)})
    return {
        'at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'resources': r.snapshot(),
        'counts': [{'phase': phase, 'status': status, 'count': n} for (phase, status), n in sorted(counts.items())],
        'active': active, 'retained_failures': failures,
        'B4_gate': r.load(ROOT / 'reports/B4_CORRECTNESS_ACCEPTANCE.json')['status'],
        'B4_completed_phases': [p.stem for p in sorted((K / 'reports').glob('*_COMPLETED.json'))],
        'B4_matrix_complete': (K / 'reports/FINITE_MATRIX_COMPLETED.json').exists(),
        'not_hardware_qualification': True,
    }

if __name__ == '__main__':
    print(json.dumps(snapshot(), indent=2))
