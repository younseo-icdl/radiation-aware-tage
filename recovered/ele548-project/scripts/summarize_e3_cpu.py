#!/usr/bin/env python3
"""Audit complete O3 phases and compare matched trials, preserving failures."""
import argparse
import csv
import copy
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SCHEMES = ['P0', 'P_ED', 'P_ECC', 'P_TMR']
CONDITION = ['mode', 'field', 'profile', 'population', 'rate', 'normalization', 'check', 'repair']


def comparable_config(config):
    """Only wrapper parameters/classes and per-run stdout/stderr paths can differ."""
    result = copy.deepcopy(config)
    conditional = result['system']['cpu']['branchPred']['conditionalBranchPred']
    if conditional['type'] == 'ResearchTAGE':
        assert conditional['cxx_class'] == 'bp::CpuTAGE'
        conditional.update(type='TAGE', cxx_class='gem5::branch_prediction::TAGE')
        tage = conditional['tage']
        assert tage['type'] == 'ResearchTAGEBase' and tage['cxx_class'] == 'bp::CpuTAGEBase'
        tage.update(type='TAGEBase', cxx_class='gem5::branch_prediction::TAGEBase')
        for name in ['check_cycles', 'repair_cycles', 'cycle_ticks', 'scheme', 'schedule_file',
                     'event_log', 'manifest_file', 'summary_file', 'read_log', 'read_log_limit']:
            del tage[name]
    for process in result['system']['cpu']['workload']:
        process['output'] = 'PER_RUN_STDOUT'
        process['errout'] = 'PER_RUN_STDERR'
    return result


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def wilson(failures, total):
    if not total:
        return None
    z = 1.959963984540054
    p = failures / total
    divisor = 1 + z*z/total
    centre = (p + z*z/(2*total))/divisor
    radius = z*np.sqrt(p*(1-p)/total + z*z/(4*total*total))/divisor
    return [max(0., float(centre-radius)), min(1., float(centre+radius))]


def estimate(values, rng, replicates):
    """Each array contains trial values within one fixed program; equal program weight."""
    if not values or any(len(a) == 0 for a in values):
        return None
    means = [float(np.mean(a)) for a in values]
    if min(map(len, values)) < 2:
        return {'mean': float(np.mean(means)), 'bootstrap95CI': None,
                'CI_status': 'insufficient independent trial seeds; engineering pilot only'}
    draws = np.zeros(replicates)
    for a in values:
        index = rng.integers(0, len(a), size=(replicates, len(a)))
        draws += np.asarray(a)[index].mean(axis=1) / len(values)
    return {'mean': float(np.mean(means)), 'bootstrap95CI': np.quantile(draws, [.025, .975]).tolist()}


def audit(report, config, phase):
    from run_e3_cpu import plan
    from run_o3_public_baseline import stats
    jobs = plan(config, phase)
    assert report['status'] != 'RUNNING', 'Phase still running; final statistics are forbidden'
    assert report['completed_runs'] == report['planned_runs'] == len(jobs)
    assert report['config_sha256'] == sha(ROOT/'configs/e3.cpu.lock.json')
    for file, key in [('reports/E3_PUBLIC_WORKLOADS.json', 'native_manifest_sha256'),
                      ('reports/E3_PUBLIC_CLEAN_BASELINE.json', 'pristine_baseline_sha256'),
                      ('sources/gem5_e3_source.lock.json', 'source_lock_sha256'),
                      ('reports/E3_INTEGRATION_GATE.json', 'gate_sha256')]:
        assert report[key] == sha(ROOT/file), f'{file} differs from campaign producer lock'
    gate = json.loads((ROOT/'reports/E3_INTEGRATION_GATE.json').read_text())
    assert report['binary_sha256'] == gate['binary_sha256']
    native = {p['name']: p for p in json.loads((ROOT/'reports/E3_PUBLIC_WORKLOADS.json').read_text())['programs']}
    baseline = {p['program']: p for p in json.loads((ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json').read_text())['programs']}
    for name, item in native.items():
        assert sha(ROOT/item['binary']) == item['binary_sha256']
        assert sha(ROOT/item['input']) == item['input_sha256']
        original = baseline[name]
        directory = ROOT/Path(original['log']).parent
        assert sha(directory/'stats.txt') == original['stats_sha256']
        assert sha(directory/'config.json') == original['config_sha256']
        raw = stats(directory/'stats.txt')
        assert original['cycles'] == int(raw['system.cpu.numCycles'])
        assert original['committed_instructions'] == int(raw['system.cpu.commitStats0.numInsts'])
        assert original['conditional_mispredictions'] == int(raw['system.cpu.branchPred.mispredicted_0::DirectCond']+raw['system.cpu.branchPred.mispredicted_0::IndirectCond'])
    baseline_configs = {name: comparable_config(json.loads((ROOT/Path(p['log']).parent/'config.json').read_text()))
                        for name, p in baseline.items()}
    manifests = {scheme: json.loads((ROOT/f'reports/e3_integration/gate/clean_{scheme}/logical_manifest.json').read_text())
                 for scheme in SCHEMES}
    expected = {t['label']: t for t in jobs}
    assert len({t['label'] for t in report['tasks']}) == len(jobs)
    assert set(expected) == {t['label'] for t in report['tasks']}
    hashes = defaultdict(set)
    zero = defaultdict(list)
    failures = []
    for t in report['tasks']:
        assert all(t[k] == v for k, v in expected[t['label']].items())
        out = ROOT/t['output']
        assert sha(out/'schedule.ticks') == t['schedule_card']['input_schedule_sha256']
        pair = (t['program'], t['mode'], t['field'], t['profile'], t['population'],
                t['rate'], t['normalization'], t['trial'], t['seed'])
        if t['population'] != 'storage_scaled_full':
            hashes[pair].add(sha(out/'schedule.ticks'))
        if t['status'] != 'PASS':
            failures.append({k: t.get(k) for k in ['label', 'status', 'error', 'log']})
            continue
        for name, key in [('stats.txt', 'stats_sha256'), ('seu.json', 'seu_sha256'),
                          ('program.stdout', 'stdout_sha256'), ('config.json', 'config_sha256')]:
            assert sha(out/name) == t[key], f'{t["label"]}: {name} changed'
        assert t['seu'] == json.loads((out/'seu.json').read_text())
        raw = stats(out/'stats.txt')
        assert t['cycles'] == int(raw['system.cpu.numCycles']), 'Reported CPU cycles disagree with original stats'
        assert t['committed_instructions'] == int(raw['system.cpu.commitStats0.numInsts']) == int(raw['simInsts']) == baseline[t['program']]['committed_instructions']
        assert t['IPC'] == raw['system.cpu.ipc']
        assert t['conditional_mispredictions'] == int(raw['system.cpu.branchPred.mispredicted_0::DirectCond']+raw['system.cpu.branchPred.mispredicted_0::IndirectCond'])
        assert t['seu']['end_tick'] == int(raw['finalTick'])
        assert t['stdout_sha256'] == native[t['program']]['native_stdout_sha256']
        assert not (out/'program.stderr').read_bytes()
        assert 'Exit cause: exiting with last active thread context code: 0' in (out/'gem5.log').read_text()
        raw_config = json.loads((out/'config.json').read_text())
        assert comparable_config(raw_config) == baseline_configs[t['program']], 'CPU/cache/clock/input config drift outside declared protection parameters'
        tage = raw_config['system']['cpu']['branchPred']['conditionalBranchPred']['tage']
        assert (tage['scheme'], tage['check_cycles'], tage['repair_cycles'], tage['cycle_ticks']) == (t['scheme'], t['check'], t['repair'], config['cycle_ticks'])
        assert json.loads((out/'logical_manifest.json').read_text()) == manifests[t['scheme']]
        assert t['committed_instructions'] > 0 and t['cycles'] > 0
        assert np.isclose(t['IPC_from_counts'], t['committed_instructions']/t['cycles'])
        assert np.isclose(t['conditional_MPKI'], 1000*t['conditional_mispredictions']/t['committed_instructions'])
        scheduled = []
        for line in (out/'schedule.ticks').read_text().splitlines():
            tick, ids = line.split()
            scheduled.append((int(tick), list(map(int, ids.split(';')))))
        applied = [(tick, ids) for tick, ids in scheduled if tick <= t['seu']['end_tick']]
        with (out/'events.csv').open() as stream:
            logs = list(csv.DictReader(stream))
        assert len(applied) == len(logs) == t['seu']['applied_events']
        assert sum(len(ids) for _, ids in applied) == t['seu']['applied_flips']
        for row, (tick, ids) in zip(logs, applied):
            assert int(row['tick']) == tick and list(map(int, row['site_ids'].split(';'))) == ids
            assert row['XOR_verified'] == '1'
        if t['mode'] == 'zero' and t['check'] == 0:
            zero[t['program']].append((t['cycles'], t['conditional_mispredictions'],
                t['seu']['canonical_base_state_hash'], t['seu']['predictor_rng_hash'],
                t['seu']['predictor_rng_draws']))
    assert all(len(s) == 1 for s in hashes.values()), 'Paired event schedules differ'
    assert all(len(set(rows)) == 1 for rows in zero.values()), 'Zero-fault state/counter/RNG mismatch'
    assert report['successful_runs'] == len(jobs)-len(failures)
    return failures


def analyze(report, config, phase, baseline):
    rng = np.random.default_rng(config['bootstrap_seed'])
    by = {t['label']: t for t in report['tasks']}
    clean = {(t['program'], t['scheme'], t['check']): t for t in by.values() if t['mode'] == 'zero'}
    # The latency phase has paired ideal faulty references but no duplicated ideal clean runs.
    pristine = {t['program']: t for t in baseline['programs']}
    fault_p0 = {}
    grouped = defaultdict(list)
    for t in by.values():
        if t['mode'] != 'zero':
            grouped[tuple(t[k] for k in CONDITION)+(t['scheme'],)].append(t)
            if t['scheme'] == 'P0':
                fault_p0[(t['program'], t['mode'], t['field'], t['profile'], t['population'],
                          t['rate'], t['normalization'], t['trial'], t['seed'])] = t
    groups = []
    for key, rows in sorted(grouped.items(), key=lambda pair: str(pair[0])):
        rows.sort(key=lambda t: (t['program'], t['trial'], t['seed'], t['label']))
        condition = dict(zip(CONDITION+['scheme'], key))
        programs = sorted({t['program'] for t in rows})
        measurements = defaultdict(lambda: defaultdict(list))
        failure_by_program = {}
        paired_count = 0
        for program in programs:
            program_rows = [t for t in rows if t['program'] == program]
            failed = sum(t['status'] != 'PASS' for t in program_rows)
            failure_by_program[program] = {'failed': failed, 'attempted': len(program_rows),
                'fraction': failed/len(program_rows), 'Wilson95CI': wilson(failed, len(program_rows))}
        for t in rows:
            if t['status'] != 'PASS':
                continue
            program = t['program']
            a = pristine[program]
            c = clean.get((program, t['scheme'], t['check']))
            if t['check'] == 0:
                clean_cycles, clean_mpki = a['cycles'], a['conditional_MPKI']
            else:
                assert c is not None and c['status'] == 'PASS', 'Valid latency clean baseline required'
                clean_cycles, clean_mpki = c['cycles'], c['conditional_MPKI']
            b = fault_p0.get((program, t['mode'], t['field'], t['profile'], t['population'],
                             t['rate'], t['normalization'], t['trial'], t['seed']))
            metrics = {'cycles': t['cycles'], 'IPC': t['IPC_from_counts'],
                'conditional_MPKI': t['conditional_MPKI'],
                'total_slowdown_pct': 100*(t['cycles']/a['cycles']-1),
                'fault_loss_pct_of_own_clean': 100*(t['cycles']/clean_cycles-1),
                'protection_clean_overhead_pct': 100*(clean_cycles/a['cycles']-1),
                'IPC_change_pct_from_own_clean': 100*(clean_cycles/t['cycles']-1),
                'delta_conditional_MPKI_from_own_clean': t['conditional_MPKI']-clean_mpki}
            for name in ['applied_events', 'applied_flips', 'unapplied_future_events', 'detected',
                         'corrected', 'DUE', 'reset_refill', 'repair_words', 'replica_repairs',
                         'response_hold_cycles', 'drain_hold_cycles', 'fallback_predictions',
                         'stale_restores_suppressed', 'stale_training_suppressed', 'repair_batches']:
                metrics[name] = t['seu'][name]
            for name, value in t['fetch_stalls'].items():
                metrics[name] = value
            if b is not None and b['status'] == 'PASS':
                metrics['benefit_pct_points_of_pristine_vs_P0_fault'] = 100*(b['cycles']-t['cycles'])/a['cycles']
                metrics['benefit_pct_relative_to_P0_fault'] = 100*(b['cycles']-t['cycles'])/b['cycles']
                paired_count += 1
            for name, value in metrics.items():
                measurements[name][program].append(float(value))
        metric_summaries = {name: estimate([values[p] for p in programs], rng, config['bootstrap_replicates'])
                            for name, values in measurements.items()}
        program_metrics = {program: {name: estimate([values[program]], rng, config['bootstrap_replicates'])
                                     for name, values in measurements.items()} for program in programs}
        groups.append(dict(condition, programs=programs, attempted_runs=len(rows),
            successful_runs=sum(t['status'] == 'PASS' for t in rows), paired_normal_exit_runs=paired_count,
            failures_by_program=failure_by_program, metrics=metric_summaries, program_metrics=program_metrics,
            mean_boundary='equal fixed-program weight; normal exits only if any failures; paired benefits require both normal exits'))
    return groups


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['pilot', 'main', 'latency'], required=True)
    args = parser.parse_args()
    path = ROOT/f'reports/E3_CPU_{args.phase.upper()}.json'
    report = json.loads(path.read_text())
    config = json.loads((ROOT/'configs/e3.cpu.lock.json').read_text())
    failures = audit(report, config, args.phase)
    baseline = json.loads((ROOT/'reports/E3_PUBLIC_CLEAN_BASELINE.json').read_text())
    groups = analyze(report, config, args.phase, baseline)
    result = {'status': 'AUDITED_COMPLETE_CPU_PHASE_WITH_FAILURES' if failures else 'PASS_AUDITED_COMPLETE_CPU_PHASE',
        'phase': args.phase, 'campaign_sha256': sha(path), 'config_sha256': sha(ROOT/'configs/e3.cpu.lock.json'),
        'analysis_source_sha256': sha(Path(__file__)), 'attempted_runs': report['planned_runs'],
        'successful_runs': report['successful_runs'], 'failures': failures, 'groups': groups,
        'statistical_contract': 'stable program/trial/seed ordering independent of host completion order; matched-seed differences, stratified seed bootstrap 2000, equal fixed-program mean; no branch-level independence or unseen-workload CI',
        'audit_contract': 'native binary/input and pristine stats/config hashes; direct original-stat counter comparison, same complete CPU/cache/clock/input config except declared wrapper parameters and output paths, logical manifest equality, event XOR/order/count and zero-fault state/RNG',
        'failure_contract': 'every failure retained in denominator and per-program Wilson interval; means conditional on normal exit, paired benefit on both normal exits; bootstrap excludes failed numerical metrics explicitly',
        'pilot_contract': 'engineering pilot is not final inference; one trial per condition cannot supply a seed-based confidence interval',
        'latency_contract': config['latency_contract'], 'physical_rate': None,
        'CPU_boundary': config['input_policy'], 'PDK_PPA_measured': False}
    destination = ROOT/f'reports/E3_CPU_{args.phase.upper()}_SUMMARY.json'
    destination.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['status', 'phase', 'attempted_runs', 'successful_runs']}))


if __name__ == '__main__':
    main()
