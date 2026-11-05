"""Post-hoc analysis only: hash-checked completed C evaluation, no new simulation."""
import collections
import csv
import hashlib
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'scripts'))
from continuation_statistics import fixed_program_bootstrap


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


campaign_path = ROOT / 'continuation_v3/runtime/reports/CPU_EVALUATION.json'
campaign = load(campaign_path)
assert campaign['status'] == 'PASS' and campaign['completed'] == 558
tasks = campaign['tasks']
by = {(t['program'], t['scenario'], t.get('owner'), t['id']): t for t in tasks}
clean = {(t['program'], t['id']): t for t in tasks if t['scenario'] == 'zero'}
stats_hashes = {}


def stats(task):
    path = ROOT / task['output'] / 'stats.txt'
    actual = sha(path)
    assert actual == task['hashes']['stats.txt']
    stats_hashes[str(path.relative_to(ROOT))] = actual
    result = {}
    for line in path.read_text().splitlines():
        fields = line.split()
        if len(fields) > 1:
            try:
                result[fields[0]] = float(fields[1])
            except ValueError:
                pass
    return result


stat_fields = {
    'committed_conditional_mispredictions': 'system.cpu.branchPred.mispredicted_0::DirectCond',
    'committed_all_mispredictions': 'system.cpu.branchPred.mispredicted_0::total',
    'rescheduled_load_attempts': 'system.cpu.lsq0.rescheduledLoads',
    'LSQ_full_events': 'system.cpu.iew.lsqFullEvents',
    'memory_order_violation_events': 'system.cpu.iew.memOrderViolationEvents',
    'icache_stall_cycles': 'system.cpu.fetchStats0.icacheStallCycles',
}
seu_fields = ['fallback_predictions', 'drains_completed', 'drain_hold_cycles',
              'response_hold_cycles', 'retire_blocked_calls', 'stale_training_suppressed',
              'detected', 'reset_refill', 'applied_events']
owner_rows = []
groups = collections.defaultdict(list)
for p in tasks:
    if p['id'] != 'V3_P' or p['scenario'] == 'zero':
        continue
    n = by[p['program'], p['scenario'], p['owner'], 'N1']
    assert n['status'] == p['status'] == 'PASS'
    for key in ['owner', 'program', 'scenario', 'input_sha256', 'schedule_sha256',
                'producer_binary_sha256', 'config_sha256', 'instructions']:
        assert n[key] == p[key], key
    program = p['program']
    A = clean[program, 'P0']['cycles']
    assert clean[program, 'N1']['cycles'] == clean[program, 'V3_P']['cycles']
    ns, ps = stats(n), stats(p)
    row = dict(program=program, scenario=p['scenario'], owner=p['owner'], A=A,
               N1_cycles=n['cycles'], P_cycles=p['cycles'],
               P_cycles_saved=n['cycles'] - p['cycles'],
               P_advantage_pp=100 * (n['cycles'] - p['cycles']) / A,
               N1_output=n['output'], P_output=p['output'])
    for label, task, parsed in [('N1', n, ns), ('P', p, ps)]:
        row[label + '_counters'] = {alias: parsed[key] for alias, key in stat_fields.items()}
        row[label + '_counters'].update({k: task['seu'][k] for k in seu_fields})
    groups[program, p['scenario']].append(row)
    owner_rows.append(row)

summary = []
for (program, scenario), rows in sorted(groups.items()):
    ci = fixed_program_bootstrap({program: [r['P_advantage_pp'] for r in rows]},
                                 iterations=10000, seed=8171026)
    means = {}
    for label in ['N1', 'P']:
        means[label] = {k: statistics.mean(r[label + '_counters'][k] for r in rows)
                        for k in rows[0][label + '_counters']}
        means[label]['cycles'] = statistics.mean(r[label + '_cycles'] for r in rows)
    summary.append(dict(program=program, scenario=scenario, owners=len(rows),
                        P_cycles_saved=statistics.mean(r['P_cycles_saved'] for r in rows),
                        P_advantage_pp=ci, mean_counters=means))

result = dict(status='POSTHOC_COMPLETED_EVIDENCE_ANALYSIS_NO_NEW_SIMULATION',
    source_campaign=str(campaign_path.relative_to(ROOT)), source_sha256=sha(campaign_path),
    analysis='Per-program matched owner comparison of N1 and P under frozen corrected C producer',
    sign='positive P advantage = 100*(N1 fault cycles - P fault cycles)/same clean P0 A',
    uncertainty='Nine exploratory program/scenario comparisons, no multiplicity adjustment; one fixed input/program and10 event owners; not a workload-population CI',
    counter_warning='LSQ_full_events and retire_blocked_calls are event/call counts, not cycle counts. Overlapping counters cannot be added into a CPI decomposition.',
    causal_warning='Observed extra drains, memory reschedules and LSQ backpressure are associations. Aggregate counters do not prove each contribution or reschedule reason.',
    clean_cycles={p:{v:clean[p,v]['cycles'] for v in ['P0','N1','V3_P']}
                  for p in ['qsort_small','dijkstra_small','sha1']},
    per_program_scenario=summary, matched_owner_rows=owner_rows, checked_stats_hashes=stats_hashes)
(OUT / 'RESULTS.json').write_text(json.dumps(result, indent=2) + '\n')
with (OUT / 'PROGRAM_COMPARISON.csv').open('w') as f:
    writer = csv.DictWriter(f, fieldnames=['program','scenario','owners','P_cycles_saved',
        'P_advantage_pp','CI95_low','CI95_high'])
    writer.writeheader()
    for row in summary:
        writer.writerow({k:row[k] for k in ['program','scenario','owners','P_cycles_saved']} |
            dict(P_advantage_pp=row['P_advantage_pp']['mean'],
                 CI95_low=row['P_advantage_pp']['CI95'][0],
                 CI95_high=row['P_advantage_pp']['CI95'][1]))
print('Hash-checked180 fault outputs; nine exploratory program/scenario comparisons; no campaign changed')
