#!/usr/bin/env python3
"""Read-only evidence checks and fixed-case summaries; launches no simulator."""
from pathlib import Path
from collections import Counter, defaultdict
import csv, hashlib, json

BASE = Path(__file__).resolve().parents[1]
OLD = Path('/home/youns/workspace/ele548-project-v9')
V10 = Path('/home/youns/workspace/ele548-project-v10')
REPORT = BASE / 'reports'

def digest(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def ref(p):
    return {'path': str(p), 'sha256': digest(p)}

def read(p):
    return json.loads(Path(p).read_text())

def save(name, obj):
    with (REPORT / name).open('x') as f:
        json.dump(obj, f, indent=2)
        f.write('\n')

def verify(item):
    assert digest(item['path']) == item['sha256'], ('CHANGED_INPUT', item['path'])

def main():
    gate = read(REPORT / 'CPP_GATE.json')
    assert gate['status'] == 'PASS_FULL_PREDICTOR_CPP_FUNCTIONAL_NOT_CPU_TIMING'
    verify(gate['source_lock']); verify(gate['compiler_dependencies'])
    source = read(gate['source_lock']['path'])
    for entry in source['original_sources'] + source['new_sources']:
        verify(entry)
    dependencies = read(gate['compiler_dependencies']['path'])
    for entry in dependencies['files']:
        verify(entry)
    # Exact installed R2 source, including its previously reviewed TAGE hooks.
    # This does not describe the patched file as an untouched upstream blob.
    r2path = OLD / 'rate_state_v9/r2/runtime/configs/source.lock.json'
    r2 = read(r2path)
    assert r2['pin'] == 'c8222cc67a399bfc01e8658dd14b30d5bfd634f9'
    checked = []
    for relative, expected in r2['transport'].items():
        p = OLD / 'third_party/gem5-native-v9r2/src' / relative
        assert digest(p) == expected, ('OLD_TRANSPORT_CHANGED', p)
        checked.append(ref(p))
    preservation = [
        (OLD / 'third_party/gem5-native-v9r2/build/X86_PIPELINE/gem5.opt',
         '194c022c89cda8754d9fdafd787338b51ab81b6e4438a9fdbd7870256f962330'),
        (V10 / 'native_lifetime_next/artifacts/BP_SEU_V10_NATIVE_LIFETIME_RESULTS.zip',
         'd97b6fdf3807463543f6ead8982bac612a7f43b87281d584a0165f3ea2b39e47'),
    ]
    for p, expected in preservation:
        assert digest(p) == expected, ('PRESERVED_PRODUCER_CHANGED', p)
    save('PRESERVATION.json', {
        'status': 'PASS_PINNED_OLD_TRANSPORT_BINARY_ARCHIVE_AND_CPP_INPUTS_UNCHANGED',
        'upstream_pin': r2['pin'], 'patched_R2_lock': ref(r2path),
        'checked_transport': checked,
        'preserved': [ref(p) for p, _ in preservation],
        'functional_sources': source['new_sources'],
        'scope': 'Selected source/SHA preservation, not a byte audit of every old directory',
        'analysis_tool': ref(Path(__file__)),
    })

    manifest_path = OLD / 'reports/predictor_logical_state_manifest.jsonl'
    sites = [json.loads(line) for line in manifest_path.read_text().splitlines()]
    assert len(sites) == 65370
    assert [s['site_id'] for s in sites] == list(range(65370))
    grouped = defaultdict(list)
    for s in sites:
        # Fold row is one of index/tag0/tag1; raw row is age, table row is entry.
        key = (s['field'], s['bank'], s['row'] if s['field'] == 'folded' else None, s['width'])
        grouped[key].append(s)
    groups = []
    for (field, bank, fold_row, width), items in grouped.items():
        ids = [s['site_id'] for s in items]
        assert ids == list(range(ids[0], ids[-1] + 1))
        groups.append({'field': field, 'bank': bank, 'fold_row': fold_row,
                       'logical_payload_width': width,
                       'first_id': ids[0], 'last_id_inclusive': ids[-1],
                       'bits': len(items), 'rows': len({s['row'] for s in items}),
                       'encoding': items[0]['encoding']})
    counts = Counter(s['field'] for s in sites)
    assert counts['raw_path'] == 146 and counts['folded'] == 200
    cpu_manifest = BASE / 'runtime/cpu_regression/qsort_small.R1.OVERWRITE/logical_manifest.json'
    extra = read(cpu_manifest)
    assert extra['base_bits'] == 65370 and extra['total_bits'] == 65522
    assert extra['direct'] == 0 and extra['removed_fold_bits'] == 0
    assert [s['id'] for s in extra['additional_sites']] == list(range(65370, 65522))
    save('LOGICAL_STATE_MANIFEST.json', {
        'status': 'FUNCTIONAL_OVERWRITE_SAME_RECURRENT_BASE_AND_NATIVE_PENDING_POPULATION',
        'base_manifest': ref(manifest_path), 'base_sites': 65370,
        'compact_ranges': groups, 'selected_S_star': {'raw': 130, 'path': 16, 'fold': 200, 'total': 346},
        'new_C0_CPU_total': 65522, 'native_endpoint_sites': extra['additional_sites'],
        'CPU_manifest': ref(cpu_manifest), 'original_exclusions': extra['excluded'],
        'added_exclusions': [
            {'storage': 'Nine uint64 Activity members (576 software bits)',
             'reason': 'Instrumentation only; never prediction, training, check or recovery operands'},
            {'storage': 'const overwrite_enabled selector',
             'reason': 'Elaboration-time candidate choice; no runtime hardware mode control proposed'},
            {'storage': 'source_fold local accumulators and loop variables',
             'reason': 'Synchronous functional reduction, no new latch/queue timing implementation'},
            {'storage': 'Inactive raw buffer retention and CPU-owned BranchInfo snapshots',
             'reason': 'Inherited logical active-window contract, not complete physical storage coverage; rollback resurrection tested explicitly'},
        ],
        'new_lookup_queues_or_epochs': 'NONE: native synchronous L0 C0 integration only',
        'coverage_limit': 'No new WHOLE campaign or complete hardware safety qualification; no timing/control implementation inferred',
    })

    pilot = read(REPORT / 'PILOT_RESULT.json')
    verify(pilot['rows']); verify(pilot['plan'])
    plan = read(pilot['plan']['path'])
    verify(plan['pilot_source'])
    for inp in plan['inputs']:
        verify(inp)
    rows = list(csv.DictReader(Path(pilot['rows']['path']).open()))
    owners = defaultdict(list)
    groups = defaultdict(list)
    for row in rows:
        owners[row['trace'], row['field'], row['owner']].append(row)
        groups[row['trace'], row['field'], row['mode']].append(row)
    assert len(owners) == 16 and all(len(v) == 7 for v in owners.values())
    for records in owners.values():
        assert len({(r['clean_misses'], r['clean_prediction_hash']) for r in records}) == 1
    summary = []
    for (trace, field, mode), records in groups.items():
        records.sort(key=lambda r: int(r['owner']))
        removed = all(r['status'] == 'STRUCTURALLY_REMOVED_NOT_EXPOSED' for r in records)
        if removed:
            assert mode == 'DIRECT' and field == 'FOLD'
            delta = None
        else:
            delta = [int(r['delta_misses']) for r in records]
            for r in records:
                assert int(r['fault_misses']) - int(r['clean_misses']) == int(r['delta_misses'])
                assert abs(float(r['delta_MPKI']) - 1000 * int(r['delta_misses']) / int(r['instruction_records'])) < 1e-12
        summary.append({'trace': plan['names'][int(trace)], 'field': field, 'method': mode,
                        'owner_order': [int(r['owner']) for r in records],
                        'delta_conditional_misses': delta,
                        'delta_MPKI_instruction_denominator': None if removed else [float(r['delta_MPKI']) for r in records],
                        'prediction_hash_matches_clean': None if removed else [r['clean_prediction_hash'] == r['fault_prediction_hash'] for r in records],
                        'status': 'STRUCTURALLY_REMOVED_NOT_EXPOSED' if removed else 'ACTUAL_FIXED_CASE_CPP_REPLAY'})
    save('PILOT_SUMMARY.json', {
        'status': 'PASS_FIXED_CASE_MATCHED_ANALYSIS_NOT_POPULATION_OR_CPU_PERFORMANCE',
        'pilot': ref(REPORT / 'PILOT_RESULT.json'), 'records': summary,
        'actual_fault_replays': 104, 'not_exposed_rows': 8, 'clean_windows': 112,
        'case_independence': '16 fixed role/offset cases; no event RNG or random-sample CI',
        'trace_scope': 'Existing HW1 CBP/SPEC2006-derived design trace windows; not SPEC CPU binaries or independent holdout',
        'rate': 'No measured per-bit rate, particle-rate conversion, Poisson/rate sweep or physical MCU mapping in this diagnostic',
        'limitations': ['Fixed actual branch stream; no wrong-path CPU feedback',
                        'No finite update latency/ports', 'Only selected raw/fold SBUs',
                        'Program and predictor table damage may outlive the 10000-control horizon'],
    })
    print(json.dumps({'status': 'PASS_FUNCTIONAL_ANALYSIS_AND_PROVENANCE',
                      'pilot_rows': len(rows), 'manifest_bits': 65522,
                      'new_CPU_or_EDA_dispatched': 0}))

if __name__ == '__main__':
    main()
