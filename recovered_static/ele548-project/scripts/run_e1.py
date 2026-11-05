#!/usr/bin/env python3
"""Preflight then fixed-size E1 campaign. Holdout metrics are never opened."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/e1.design.lock.json'


def sha(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()


def read_csv(p):
    with p.open() as f: return list(csv.DictReader(f))


def run_command(command, log, timeout):
    with log.open('w') as f:
        try:
            p = subprocess.run(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=timeout)
        except subprocess.TimeoutExpired:
            return {'status': 'FAIL_TIMEOUT', 'command': command, 'log': str(log.relative_to(ROOT))}
    return {'status': 'PASS' if p.returncode == 0 else 'FAIL_EXECUTION', 'exit_code': p.returncode,
            'command': command, 'log': str(log.relative_to(ROOT))}


def validate_rows(path, expected, c):
    rows = read_csv(path)
    assert len(rows) == expected
    for r in rows:
        assert r['status'] == 'PASS'
        assert int(r['post_branches']) == c['post_event_horizon_conditional_branches']
        assert int(r['net']) == int(r['harm']) - int(r['help']) == int(r['faulty_misses']) - int(r['clean_misses'])
        assert math.isclose(float(r['delta_MPKI']), 1000 * int(r['net']) / int(r['instructions']), rel_tol=1e-12, abs_tol=1e-12)
        assert 0 <= int(r['inject_offset']) < c['injection_prefix_conditional_branches']
        ids = r['event_site_ids'].split(';')
        if r['model'] != 'ZERO': assert len(ids) == len(set(ids)) == int(r['multiplicity'])
        for h in c['cumulative_checkpoints']:
            assert int(r[f'net_{h}']) == int(r[f'harm_{h}']) - int(r[f'help_{h}'])
            if r['model'] == 'ZERO': assert int(r[f'all_residual_{h}']) == 0 and r[f'observed_semantic_equal_{h}'] == '1'
    return rows


def task_command(c, item, model, n, seed, warmup, output):
    windex, workload, path = item
    weights = c['K_profiles'].get(model, {'1': 1, '2': 0})
    return [str(ROOT / 'build/e1_campaign'), str(path), workload, str(windex),
            str(c['design_anchor_conditional_ordinal']), str(warmup),
            str(c['injection_prefix_conditional_branches']), str(c['post_event_horizon_conditional_branches']),
            str(n), str(weights['1']), str(weights['2']), model, str(seed), str(output)]


def preflight(c, inputs, outdir):
    warm_tasks = []
    def warm(item):
        _, workload, path = item
        output = outdir / f'{workload}.warmup.csv'
        command = [str(ROOT / 'build/e1_warmup'), str(path), workload,
                   str(c['design_anchor_conditional_ordinal']), str(c['warmup_metric_window_conditional_branches']), str(output)]
        status = run_command(command, outdir / f'{workload}.warmup.log', c['per_task_timeout_seconds'])
        if status['status'] != 'PASS': raise RuntimeError(json.dumps(status))
        rows = read_csv(output)
        assert len(rows) == len(c['warmup_candidates_conditional_branches'])
        table = {int(r['warmup_branches']): float(r['MPKI']) for r in rows}
        limit_400 = max(.1, .05 * table[400000]); limit_500 = max(.1, .05 * table[500000])
        return {'workload': workload, 'rows': rows, 'stability_200k_vs_400k': abs(table[200000] - table[400000]) <= limit_400,
                'stability_400k_vs_500k': abs(table[400000] - table[500000]) <= limit_500,
                'CSV': str(output.relative_to(ROOT)), 'CSV_sha256': sha(output)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=c['workers']) as pool:
        warm_tasks = list(pool.map(warm, inputs))
    warmup = 400000 if all(x['stability_200k_vs_400k'] for x in warm_tasks) else 500000
    statuses, outputs = [], {}
    for label, model, n in [('zero', 'ZERO', 1), ('speed60', 'M0', 10), ('repeat6', 'M0', 1)]:
        output = outdir / f'{label}.csv'
        start = time.perf_counter()
        status = run_command(task_command(c, inputs[0], model, n, c['calibration_seed_base'], warmup, output),
                             outdir / f'{label}.log', c['per_task_timeout_seconds'])
        if status['status'] != 'PASS': raise RuntimeError(json.dumps(status))
        rows = validate_rows(output, n * 6, c); outputs[label] = rows
        status.update(trials=len(rows), wall_seconds=time.perf_counter()-start,
                      mean_trial_seconds=statistics.mean(float(r['wall_seconds']) for r in rows),
                      max_RSS_KiB=max(int(r['peak_rss_kib']) for r in rows))
        statuses.append(status)
    ignored = {'wall_seconds', 'peak_rss_kib'}
    for repeated in outputs['repeat6']:
        original = next(r for r in outputs['speed60'] if r['field'] == repeated['field'] and r['trial'] == '0')
        assert {k:v for k,v in repeated.items() if k not in ignored} == {k:v for k,v in original.items() if k not in ignored}
    cost = statuses[1]['mean_trial_seconds']
    planned = c['planned_M0_trials'] + c['planned_CHARM_trials']
    result = {'status': 'PASS_PREFLIGHT_EQUAL_FOLLOWUP_INJECTION', 'config_sha256': sha(CONFIG),
              'correctness_log': 'reports/e1_correctness.log', 'primary_warmup_branches_used': warmup,
              'warmup': warm_tasks, 'tests': statuses, 'predictor_trials_before_main': 72,
              'schedule_impact_determinism': 'PASS_6_REPEATS',
              'planned_main_trials': planned, 'projected_main_seconds_serial_trial_work': planned * cost,
              'workers': c['workers'], 'runtime_projection_limit': 'first workload estimate; excludes startup/cache work and workload-dependent variance',
              'full_prefix_warmup': warmup == 500000,
              'stability': 'PASS_200K_400K_ALL' if warmup == 400000 else ('FULL_PREFIX_500K_400K_STABLE' if all(x['stability_400k_vs_500k'] for x in warm_tasks) else 'FULL_PREFIX_FINITE_TRACE_WITH_REMAINING_SENSITIVITY'),
              'holdout_performance_evaluated': False,
              'binary_sha256': sha(ROOT / 'build/e1_campaign'), 'warmup_binary_sha256': sha(ROOT / 'build/e1_warmup')}
    (ROOT / 'reports/E1_PREFLIGHT.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['status', 'primary_warmup_branches_used', 'stability', 'predictor_trials_before_main', 'projected_main_seconds_serial_trial_work']}, indent=2), flush=True)


def campaign(c, inputs, outdir):
    check = json.loads((ROOT / 'reports/E1_PREFLIGHT.json').read_text())
    assert check['status'] == 'PASS_PREFLIGHT_EQUAL_FOLLOWUP_INJECTION' and check['config_sha256'] == sha(CONFIG)
    assert check['binary_sha256'] == sha(ROOT / 'build/e1_campaign')
    warmup = check['primary_warmup_branches_used']
    start = time.perf_counter()
    jobs = [(item, model, c['M0_trials_per_workload_field'] if model == 'M0' else c['CHARM_trials_per_profile_workload_field'])
            for model in c['K_profiles'] for item in inputs]
    outputs, failures = [], []
    def run(job):
        item, model, n = job
        key = f'{item[1]}.{model}'; output = outdir / (key + '.csv')
        status = run_command(task_command(c, item, model, n, c['main_seed_base'], warmup, output),
                             outdir / (key + '.log'), c['per_task_timeout_seconds'])
        status.update(workload=item[1], model=model, planned_trials=n*6, output=str(output.relative_to(ROOT)))
        if status['status'] == 'PASS':
            try:
                rows=validate_rows(output,n*6,c)
                status.update(successful_trials=len(rows),CSV_sha256=sha(output))
            except Exception as error: status.update(status='FAIL_VALIDATION',error=str(error))
        return status
    report_path = ROOT / 'reports/E1_CAMPAIGN.json'
    report_path.write_text(json.dumps({'status':'RUNNING','planned_trials':sum(j[2]*6 for j in jobs),'holdout_performance_evaluated':False},indent=2)+'\n')
    with concurrent.futures.ThreadPoolExecutor(max_workers=c['workers']) as pool:
        future_map = {pool.submit(run, job): job for job in jobs}
        for future in concurrent.futures.as_completed(future_map):
            result = future.result()
            (outputs if result['status'] == 'PASS' else failures).append(result)
            print(json.dumps({k:result.get(k) for k in ['workload','model','status','successful_trials']},ensure_ascii=False),flush=True)
    rows = []
    for item in outputs: rows += read_csv(ROOT / item['output'])
    aggregate=outdir/'trials.csv'
    if rows:
        with aggregate.open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    planned=sum(j[2]*6 for j in jobs)
    assert planned == c['planned_M0_trials'] + c['planned_CHARM_trials']
    result={'status':'PASS_FIXED_DESIGN_E1_CAMPAIGN' if not failures else 'FAIL_EXECUTION_OR_VALIDATION',
            'config_sha256':sha(CONFIG),'input_manifest_sha256':sha(ROOT/'reports/E1_WORKLOAD_WINDOWS.json'),
            'binary_sha256':sha(ROOT/'build/e1_campaign'),'planned_trials':planned,'successful_trials':len(rows),
            'failures':failures,'tasks':outputs,'wall_seconds':time.perf_counter()-start,
            'max_RSS_KiB':max((int(r['peak_rss_kib']) for r in rows),default=None),
            'primary_warmup_branches':warmup,'post_event_branches':c['post_event_horizon_conditional_branches'],
            'trial_CSV':str(aggregate.relative_to(ROOT)),'trial_CSV_sha256':sha(aggregate) if rows else None,
            'holdout_performance_evaluated':False,'CPU_cycles_IPC_measured':False,
            'budget':'fixed 3600 SBU + 2160 CHARM source-sensitivity trials; no optional stopping'}
    report_path.write_text(json.dumps(result,indent=2)+'\n')
    if failures: raise SystemExit(1)


def main():
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=['preflight','main'],required=True);a=p.parse_args()
    c=json.loads(CONFIG.read_text());manifest=json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())
    assert manifest['status']=='PASS_COMPLETE_DISJOINT_REAL_WINDOWS'
    assert manifest['config_sha256']==sha(CONFIG)
    for model,cell in [('M1_CHARM_6T','6t'),('M1_CHARM_8T','8t')]:
        assert c['K_profiles'][model]==json.loads((ROOT/f'data/curated/charm_{cell}_tableII.json').read_text())['multiplicity_counts']
    byname={item['workload']:item for item in manifest['workloads']}
    inputs=[]
    for i,name in enumerate(c['workloads']):
        window=byname[name]['split_files']['design'];path=ROOT/window['path']
        assert sha(path)==window['sha256'],path
        inputs.append((i,name,path))
    outdir=ROOT/'reports/e1'/a.phase;outdir.mkdir(parents=True,exist_ok=True)
    preflight(c,inputs,outdir) if a.phase=='preflight' else campaign(c,inputs,outdir)


if __name__=='__main__':main()
