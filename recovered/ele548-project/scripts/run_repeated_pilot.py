#!/usr/bin/env python3
"""Run the fixed <=100-run Poisson/CHARM P0 integration pilot."""
import csv
import hashlib
import json
import math
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    config_path = ROOT / 'configs/repeated_pilot.lock.json'
    config = json.loads(config_path.read_text())
    windows_path = ROOT / config['workload_windows']
    windows = {x['name']: x for x in json.loads(windows_path.read_text())['workloads']}
    outdir = ROOT / 'reports/repeated_pilot'
    outdir.mkdir(exist_ok=True)
    profiles = [('M0_SBU', {'1': 1, '2': 0})]
    bindings = {str(config_path.relative_to(ROOT)): sha(config_path),
                str(windows_path.relative_to(ROOT)): sha(windows_path)}
    for cell in ['6t', '8t']:
        p = ROOT / f'data/curated/charm_{cell}_tableII.json'
        profiles.append((f'M1_CHARM_{cell.upper()}', json.loads(p.read_text())['multiplicity_counts']))
        bindings[str(p.relative_to(ROOT))] = sha(p)
    bindings['build/repeated'] = sha(ROOT / 'build/repeated')
    rows, arrivals, failures = [], {}, []
    start = time.perf_counter()
    for windex, workload in enumerate(config['workloads']):
        source = ROOT / windows[workload]['window_file']
        if sha(source) != windows[workload]['window_sha256']:
            raise RuntimeError(f'changed trace window: {source}')
        for model, counts in profiles:
            for rindex, rate in enumerate(config['event_rates_per_conditional_branch']):
                for rep in range(config['replicates_per_workload_profile_rate']):
                    key = f'{workload}_{model}_r{rindex}_s{rep}'
                    seed = config['seed_base'] + windex * 10000 + rep * 10
                    output, event_path, log = [outdir / (key + suffix) for suffix in ['.csv', '.events.csv', '.log']]
                    command = [str(ROOT / 'build/repeated'), str(source), str(rate),
                               str(seed), str(seed + 1), str(seed + 2), str(counts['1']),
                               str(counts['2']), model, str(output), str(event_path)]
                    with log.open('w') as f:
                        try:
                            result = subprocess.run(command, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT,
                                                    timeout=config['per_run_timeout_seconds'])
                        except subprocess.TimeoutExpired:
                            failures.append({'run': key, 'class': 'FAIL_TIMEOUT'}); continue
                    if result.returncode:
                        failures.append({'run': key, 'class': 'FAIL_EXECUTION', 'exit': result.returncode}); continue
                    samples = list(csv.DictReader(output.open()))
                    assert len(samples) == 1
                    row = samples[0]
                    row.update(workload=workload, replicate=rep, run=key)
                    assert row['status'] == 'PASS'
                    events = list(csv.DictReader(event_path.open()))
                    assert len(events) == int(row['event_count'])
                    assert sum(int(x['multiplicity']) for x in events) == int(row['flip_count'])
                    for e in events:
                        ids = [int(x) for x in e['event_site_ids'].split(';')]
                        assert len(ids) == len(set(ids)) == int(e['multiplicity'])
                        assert 0 <= float(e['arrival_branch_coordinate']) < 10000
                        assert math.floor(float(e['arrival_branch_coordinate'])) == int(e['applied_before_conditional_ordinal'])
                    assert int(row['net']) == int(row['harm']) - int(row['help'])
                    assert int(row['net']) == int(row['faulty_misses']) - int(row['clean_misses'])
                    schedule_key = (workload, rindex, rep)
                    t = [e['arrival_branch_coordinate'] for e in events]
                    if schedule_key in arrivals:
                        assert t == arrivals[schedule_key], 'source K changed arrival RNG'
                    arrivals[schedule_key] = t
                    if rate == 0:
                        assert int(row['event_count']) == int(row['end_differing_logical_bits']) == int(row['net']) == 0
                    bindings[str(event_path.relative_to(ROOT))] = sha(event_path)
                    rows.append(row)
    aggregate = outdir / 'runs.csv'
    if rows:
        with aggregate.open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator='\n')
            writer.writeheader(); writer.writerows(rows)
        bindings[str(aggregate.relative_to(ROOT))] = sha(aggregate)
    groups = []
    for workload in config['workloads']:
        for model, counts in profiles:
            ek = (counts['1'] + 2 * counts['2']) / sum(counts.values())
            for rate in config['event_rates_per_conditional_branch']:
                subset = [r for r in rows if r['workload'] == workload and r['model'] == model and float(r['event_rate_per_conditional_branch']) == rate]
                groups.append({'workload': workload, 'model': model, 'event_rate_per_conditional_branch': rate,
                               'expected_event_count_per_run': rate * 10000,
                               'expected_flip_count_per_run': rate * 10000 * ek,
                               'successful_runs': len(subset), 'events': sum(int(x['event_count']) for x in subset),
                               'flips': sum(int(x['flip_count']) for x in subset),
                               'mean_net_extra_misses': statistics.mean(int(x['net']) for x in subset) if subset else None,
                               'runs_with_prediction_divergence': sum(int(x['harm']) + int(x['help']) > 0 for x in subset)})
    assert len(rows) + len(failures) == config['total_runs'] <= 100
    report = {'status': 'PASS_BOUNDED_REPEATED_P0_INJECTION' if not failures else 'FAIL_EXECUTION',
              'planned_runs': config['total_runs'], 'successful_runs': len(rows), 'failures': failures,
              'wall_seconds': time.perf_counter() - start,
              'max_RSS_KiB': max((int(x['peak_rss_kib']) for x in rows), default=None),
              'total_events': sum(int(x['event_count']) for x in rows),
              'total_flip_operations': sum(int(x['flip_count']) for x in rows),
              'same_event_rate_matching': 'PASS identical arrival times across all three profiles',
              'zero_rate_state_rng_equivalence': 'PASS' if not failures else 'SEE_FAILURES',
              'group_summaries': groups, 'hashes': bindings,
              'inference': 'engineering pilot only, no ranking/CI/physical rate claims; each complete run is a statistical unit',
              'mapping': config['location'], 'time_basis': 'conditional_branch_exposure',
              'target_per_second_rate_calibrated': False, 'S_star': None,
              'remaining': ['equal-followup single-event E1 and warmup/window checks', 'disjoint input holdout and scope freeze',
                            'same S* E2 P_ED/P_ECC/P_TMR integration', 'CERN cluster semantic gate',
                            'gem5 tick scheduler validation and actual hardware timing for final E3/E4 comparison']}
    (ROOT / 'reports/REPEATED_INJECTION_PILOT.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['status', 'planned_runs', 'successful_runs', 'failures', 'wall_seconds', 'max_RSS_KiB', 'total_events', 'total_flip_operations']}, indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
