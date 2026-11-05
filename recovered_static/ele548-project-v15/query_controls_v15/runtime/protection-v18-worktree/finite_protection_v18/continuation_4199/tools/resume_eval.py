"""Resume only the 38 never-started B4 EVAL tasks under actual CPU4199 approval."""
import collections
import datetime
import importlib.util
import math
import os
import pathlib
import subprocess
import sys
import traceback

sys.dont_write_bytecode = True
os.environ['V18_PRODUCER'] = 'B4'
ROOT = pathlib.Path(__file__).resolve().parents[2]
K = ROOT / 'runtime/continuation_b4'
TOOLS = ROOT / 'continuation_b4/tools'
sys.path.insert(0, str(TOOLS))
sys.path.insert(1, str(ROOT / 'tools'))
import campaign as p
import analyze
r = p.r
c = p.c


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def verify_closed(task):
    record = pathlib.Path(task['output']) / 'EXECUTION.json'
    row = r.load(record)
    assert row['task'] == task and row['status'].startswith('PASS'), ('PRIOR_ROW_NOT_MATCHING_FROZEN_TASK', task['label'])
    for name, sha in row['hashes'].items():
        assert r.sha(record.parent / name) == sha, ('PRIOR_RAW_CHANGED', task['label'], name)
    return r.ref(record)


def run():
    state = r.snapshot()
    assert state['CPU_cap'] == 4199 and state['CPU_global'] == 4161 and state['active'] == 0
    authority = ROOT / 'reports/CPU_4199_AUTHORIZATION.lock.json'
    assert r.load(authority)['actual_reply'] == '4,199회로 확대하고 진행'
    gate = ROOT / 'reports/B4_CORRECTNESS_ACCEPTANCE.json'
    assert r.load(gate)['status'].startswith('PASS')
    producer = c.prepare_producer()
    for ref in [producer['binary'], producer['config'], producer['observer'], *producer['actual_dependencies'], *producer['execution_tools']]:
        c.checked(ref)
    c.source_lock_checked(producer['source_lock'])
    full_path = K / 'runtime/configs/EVAL_FAULT_FULL.lock.json'
    plan_path = K / 'runtime/configs/EVAL_FAULT_PLAN.lock.json'
    tasks = r.load(full_path)['tasks']
    assert tasks == r.load(plan_path)['tasks'] and len(tasks) == 408
    prior, pending = [], []
    for task in tasks:
        output = pathlib.Path(task['output'])
        if (output / 'EXECUTION.json').exists():
            prior.append(verify_closed(task))
        else:
            assert not output.exists(), ('STARTED_WITHOUT_TERMINAL_RECORD', task['label'])
            for key in ('program_binary', 'input', 'expected_stdout', 'schedule', 'architectural_reference'):
                if key in task:
                    c.checked(task[key])
            pending.append(task)
    assert len(prior) == 370 and len(pending) == 38
    assert set(t['program'] for t in pending) == {'sha1'}
    assert not (K / 'reports/EVAL_FAULT_COMPLETED.json').exists()
    assert not (K / 'reports/EVAL_ANALYSIS.json').exists()
    assert not (K / 'reports/FINITE_MATRIX_COMPLETED.json').exists()
    samples = []
    for ref in prior:
        row = r.load(ref['path'])
        if row['program'] == 'sha1':
            used_kib = int(subprocess.check_output(['du', '-sk', str(pathlib.Path(ref['path']).parent)], text=True).split()[0])
            samples.append({'host_cpu_seconds': row['host_cpu_seconds'], 'allocated_MiB': used_kib / 1024})
    # Admission keeps output growth AND the original guard's 1MiB/active reserve.
    case_growth = math.ceil(max(x['allocated_MiB'] for x in samples) * 1.2 * 20) / 20
    preflight = {'status': 'PASS_UNCHANGED_B4_GATE_PRODUCER_AND370_CLOSED_ROWS_38_NEVER_STARTED', 'at_UTC': utc(), 'authority': r.ref(authority), 'original_full_plan': r.ref(full_path), 'original_event_plan': r.ref(plan_path), 'producer': r.ref(ROOT / 'reports/PRODUCER_B4.lock.json'), 'gate': r.ref(gate), 'source_dispatcher': r.ref(__file__), 'preserved_completed_rows': prior, 'pending_exact_tasks': pending, 'same_output_input_seed_schedule_timeout_model': True, 'case_growth_MiB_forecast': case_growth, 'sample_SHA_host_seconds': [x['host_cpu_seconds'] for x in samples], 'unchanged_limits': 'CPU4199, round160coreh, namespace1024MiB, shared32', 'resources_before': state, 'old_stop_reason': 'CPU4161 cap; old dispatcher message ACTUAL_COREH_LIMIT_NO_NEW_TRIAL was generic, not core-hours exhaustion', 'old_stop': r.ref(K / 'reports/B4_ROUND_STOP_630.json')}
    r.put(K / 'reports/RESUME_4199_PRECHECK.json', preflight)
    offset = 370
    while pending:
        state = r.snapshot()
        disk_width = max(0, int((1024 - state['round_disk_MiB'] - 2) // (1 + case_growth)))
        width = min(32, len(pending), state['CPU_cap'] - state['CPU_global'], int((160 - state['round_recorded_coreh']) * 3600 // 3605), disk_width)
        assert width > 0, ('RESUME_BUDGET_CANNOT_ADMIT_UNSTARTED_TASK', state, case_growth)
        r.snapshot(extra_MiB=2 + width * (1 + case_growth))
        batch = pending[:width]
        print('RESUME_4199_DISPATCH', offset, width, 'forecast_case_MiB', case_growth, flush=True)
        good, rows = c.batch('B4_EVAL_FAULT_4199_CHUNK_' + str(offset), batch, width)
        assert good, ('NEW_FAILURE_RETAINED_NO_AUTORETRY', [x['label'] for x in rows if not x['status'].startswith('PASS')])
        pending = pending[width:]
        offset += len(rows)
        print('EVAL_FAULT_TERMINAL', offset, '/408', flush=True)
    completed = [verify_closed(t) for t in tasks]
    assert r.snapshot()['CPU_global'] == 4199 and r.snapshot()['active'] == 0
    # Existing partial audit/STOP, marker, plans, raw, and handoff stay immutable.
    r.put(K / 'reports/EVAL_FAULT_COMPLETED.json', {'status': 'PASS', 'actual_runs': 408, 'runs': completed, 'plan': r.ref(full_path), 'resume_authority': r.ref(authority), 'resume_precheck': r.ref(K / 'reports/RESUME_4199_PRECHECK.json'), 'resources': r.snapshot()})
    result = analyze.summarize('EVAL')
    assert result['attempted_faults'] == result['valid_faults'] == 408 and result['failure_count'] == 0
    assert all(x['valid_pairs'] == 8 and x['failed_pairs'] == 0 for x in result['paired_summaries'])
    r.put(K / 'reports/EVAL_ANALYSIS.json', result)
    r.put(K / 'reports/FINITE_MATRIX_COMPLETED.json', {'status': 'ALL_FINITE_PIPELINE_DEVELOPMENT_EVALUATION_TERMINAL', 'at_UTC': utc(), 'native_reference6_complete_and_separate': True, 'resume_authority': r.ref(authority), 'resources': r.snapshot()})
    # The old finalizer wrote an INCOMPLETE audit. Use a documented report-only
    # derivative with new destination names; no predictor or execution-tool edits.
    original = TOOLS / 'finalize_b4.py'
    text = original.read_text()
    for a, b in [('ACTUAL_TERMINAL_AUDIT.json', 'ACTUAL_TERMINAL_AUDIT_4199.json'), ('ACTUAL_TERMINAL_REPORT.ko.md', 'ACTUAL_TERMINAL_REPORT_4199.ko.md')]:
        assert a in text
        text = text.replace(a, b)
    derivative = pathlib.Path(__file__).parent / 'finalize_4199.py'
    with derivative.open('x') as f:
        f.write(text)
    r.put(K / 'reports/FINALIZER_4199_DERIVATION.json', {'status': 'REPORT_PATH_ONLY_DERIVATIVE_OLD_AUDIT_PRESERVED', 'original': r.ref(original), 'derived': r.ref(derivative), 'changes': ['ACTUAL_TERMINAL_AUDIT.json -> ACTUAL_TERMINAL_AUDIT_4199.json', 'ACTUAL_TERMINAL_REPORT.ko.md -> ACTUAL_TERMINAL_REPORT_4199.ko.md'], 'predictor_source_or_binary_changed': False})
    spec = importlib.util.spec_from_file_location('finalize_4199', derivative)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.audit()
    import native_break_even_b4
    native_break_even_b4.derive()
    r.put(K / 'reports/RESUME_4199_COMPLETED.json', {'status': 'PASS_38_NEW_EVAL_ALL408_COMPLETE_SOURCE_AND_RAW_AUDITED', 'at_UTC': utc(), 'new_CPU': 38, 'final_audit': r.ref(K / 'reports/ACTUAL_TERMINAL_AUDIT_4199.json'), 'analysis': r.ref(K / 'reports/EVAL_ANALYSIS.json'), 'old_partial_audit_preserved': r.ref(K / 'reports/ACTUAL_TERMINAL_AUDIT.json'), 'resources': r.snapshot()})
    print('RESUME_4199_COMPLETE', flush=True)


if __name__ == '__main__':
    try:
        run()
    except Exception as exc:
        r.put(K / 'reports/RESUME_4199_STOP.json', {'status': 'STOP_WITH_RAW_PRESERVED_NO_RETRY', 'at_UTC': utc(), 'exception': repr(exc), 'traceback': traceback.format_exc()})
        raise
