#!/usr/bin/env python3
"""Conditional provider-cluster shape replay, with auditable hypothetical mappings."""
import argparse
import concurrent.futures
import csv
import hashlib
import json
import math
import subprocess
import time
from collections import Counter
from pathlib import Path

import numpy as np
from parse_cern_clusters import parse

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT/'configs/cern_footprint.lock.json'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def translations(offsets, width=16, height=22, valid=346):
    return [(x, y) for y in range(height) for x in range(width)
            if all(0 <= x+dx < width and 0 <= y+dy < height and (y+dy)*width+x+dx < valid
                   for dx, dy in offsets)]


def tile_mappings(scope):
    words = [w['site_ids'] for w in scope['payload_words']]
    contiguous = [bit for word in words for bit in word]
    interleaved = [word[i] for i in range(max(map(len, words))) for word in words if i < len(word)]
    assert len(contiguous) == len(interleaved) == len(set(contiguous)) == 346
    assert set(contiguous) == set(interleaved)
    return {'word_contiguous': contiguous, 'word_interleaved': interleaved,
            'dispersed_same_K': contiguous}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['pilot', 'main'], required=True)
    args = parser.parse_args()
    c = json.loads(CONFIG.read_text())
    card_path = ROOT/'data/curated/cern_footprint_model_card.json'
    card = json.loads(card_path.read_text())
    assert card['status'] == 'QUALIFIED_CONDITIONAL_PROVIDER_CLUSTER_FOOTPRINT_SENSITIVITY'
    assert sha(ROOT/'sources/protection_scope.lock.json') == c['scope_sha256']
    scope = json.loads((ROOT/'sources/protection_scope.lock.json').read_text())
    maps = tile_mappings(scope)
    word_of = {bit: w['word_id'] for w in scope['payload_words'] for bit in w['site_ids']}
    catalog = {}
    inputs = {f['file']: f for f in card['files']}
    for name in c['files']:
        path = ROOT/'data/raw/cern'/name
        assert sha(path) == inputs[name]['raw_sha256']
        rows = [r for r in parse(path.read_text()) if r['multiplicity_from_unique_coordinates'] >= 2]
        for row in rows:
            row['valid_translations'] = translations(row['offsets_from_anchor'])
            assert row['valid_translations'], f'Cannot fit entire shape {name}:{row["cluster_id"]}'
        assert len(rows) == inputs[name]['conditional_K_ge_2_records']
        catalog[name] = rows
    binary = ROOT/'build/scheduled'
    if args.phase == 'main':
        pilot = json.loads((ROOT/'reports/CERN_FOOTPRINT_PILOT.json').read_text())
        assert pilot['status'] == 'PASS_CONDITIONAL_FOOTPRINT_PILOT'
        assert pilot['config_sha256'] == sha(CONFIG) and pilot['binary_sha256'] == sha(binary)
    windows = {w['workload']: ROOT/w['split_files']['holdout']['path']
               for w in json.loads((ROOT/'reports/E1_WORKLOAD_WINDOWS.json').read_text())['workloads']}
    out = ROOT/'reports/cern_footprints'/args.phase
    out.mkdir(parents=True, exist_ok=True)
    mapping_path = ROOT/'sources/cern_hypothetical_mapping_manifest.json'
    mapping_path.write_text(json.dumps({'scope_id': c['scope_id'], 'hypothetical_tile': c['hypothetical_tile'],
        'mapping_cell_order': maps, 'measured_physical_layout': False,
        'extras_excluded': c['extra_storage_exposure']}, indent=2)+'\n')
    jobs = []
    for wi, workload in enumerate(c['workloads'][:1] if args.phase == 'pilot' else c['workloads']):
        for name in c['files']:
            for mode in c['modes']:
                norms = ['equal_event'] if args.phase == 'pilot' or mode == 'single' else c['repeat_normalizations']
                n = 1 if args.phase == 'pilot' else c['single_trials_per_condition'] if mode == 'single' else c['repeat_trials_per_condition']
                for norm in norms:
                    for trial in range(n):
                        jobs.append((wi, workload, name, mode, norm, trial))
    expected = c['pilot_trials'] if args.phase == 'pilot' else c['main_trials']
    assert len(jobs)*len(c['mappings'])*len(c['schemes']) == expected
    H = c['horizon_conditional_branches']
    report_path = ROOT/f'reports/CERN_FOOTPRINT_{args.phase.upper()}.json'
    report_path.write_text(json.dumps({'status': 'RUNNING', 'planned_trials': expected})+'\n')
    started = time.perf_counter()

    def run(job):
        wi, workload, name, mode, norm, trial = job
        seed = (c['pilot_seed_base'] if args.phase == 'pilot' else c['main_seed_base'])+wi*1000000+trial
        clock = np.random.Generator(np.random.PCG64(seed))
        marks = np.random.Generator(np.random.PCG64(seed+1))
        geo = np.random.Generator(np.random.PCG64(seed+2))
        dispersed = np.random.Generator(np.random.PCG64(seed+3))
        phase = int(clock.integers(0, c['anchor_phase_range']))
        rows = catalog[name]
        mean_k = inputs[name]['conditional_mean_K']
        rate = c['base_cluster_rate_per_conditional']/(mean_k if norm == 'equal_expected_flip' else 1)
        coordinates = [0.] if mode == 'single' else []
        if mode == 'repeat':
            coordinate = 0.
            while True:
                coordinate += float(clock.exponential(1/rate))
                if coordinate >= H:
                    break
                coordinates.append(coordinate)
        shape_records = []
        events = {mapping: [] for mapping in maps}
        for coordinate in coordinates:
            row = rows[int(marks.integers(0, len(rows)))]
            x, y = row['valid_translations'][int(geo.integers(0, len(row['valid_translations'])))]
            cells = [(y+dy)*16+x+dx for dx, dy in row['offsets_from_anchor']]
            k = row['multiplicity_from_unique_coordinates']
            assert len(set(cells)) == len(cells) == k
            sites = {mapping: [maps[mapping][cell] for cell in cells] for mapping in c['mappings'][:2]}
            sites['dispersed_same_K'] = [maps['dispersed_same_K'][int(i)]
                for i in dispersed.choice(346, size=k, replace=False)]
            for mapping, ids in sites.items():
                assert len(ids) == len(set(ids)) == k and all(bit in word_of for bit in ids)
                events[mapping].append((coordinate, ids))
            shape_records.append({'coordinate': coordinate, 'source_cluster_id': row['cluster_id'],
                'K': k, 'source_offsets': row['offsets_from_anchor'], 'hypothetical_anchor': [x, y],
                'valid_translation_count': len(row['valid_translations']), 'logical_sites': sites,
                'max_bits_in_one_word': {m: max(Counter(word_of[bit] for bit in ids).values()) for m, ids in sites.items()}})
        job_key = f'{workload}.{Path(name).stem}.{mode}.{norm}.n{trial}'
        folder = out/job_key
        folder.mkdir(exist_ok=True)
        shape_path = folder/'source_shapes.jsonl'
        shape_path.write_text(''.join(json.dumps(row)+'\n' for row in shape_records))
        output = []
        for mapping in c['mappings']:
            schedule = folder/f'{mapping}.timing'
            schedule.write_text(''.join(f'{t:.17g} '+ ';'.join(map(str, ids))+'\n' for t, ids in events[mapping]))
            common = {'workload': workload, 'source_file': name, 'mode': mode, 'normalization': norm,
                'mapping': mapping, 'trial': trial, 'seed': seed, 'anchor_phase': phase,
                'event_rate_per_conditional': rate if mode == 'repeat' else None,
                'expected_flip_rate_per_conditional': rate*mean_k if mode == 'repeat' else None,
                'source_mean_K_conditional': mean_k, 'source_raw_sha256': inputs[name]['raw_sha256'],
                'shape_manifest': str(shape_path.relative_to(ROOT)), 'shape_manifest_sha256': sha(shape_path),
                'schedule': str(schedule.relative_to(ROOT)), 'schedule_sha256': sha(schedule),
                'scheduled_events': len(coordinates), 'scheduled_flips': sum(r['K'] for r in shape_records),
                'multi_bit_word_events': sum(r['max_bits_in_one_word'][mapping] >= 2 for r in shape_records),
                'three_plus_same_word_events': sum(r['max_bits_in_one_word'][mapping] >= 3 for r in shape_records)}
            for scheme in c['schemes']:
                prefix = folder/f'{mapping}.{scheme}'
                command = [str(binary), str(windows[workload]), str(c['holdout_anchor_base']+phase),
                    str(H), scheme, str(schedule), job_key, str(prefix)]
                record = dict(common, scheme=scheme, command=command, log=str(Path(str(prefix)+'.log').relative_to(ROOT)))
                begin = time.perf_counter()
                with Path(str(prefix)+'.log').open('w') as stream:
                    try:
                        process = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
                            timeout=c['per_task_timeout_seconds'])
                    except subprocess.TimeoutExpired:
                        output.append(dict(record, status='FAIL_TIMEOUT'))
                        continue
                record.update(wall_seconds=time.perf_counter()-begin, exit_code=process.returncode)
                if process.returncode:
                    output.append(dict(record, status='FAIL_EXECUTION'))
                    continue
                try:
                    csv_path = Path(str(prefix)+'.csv')
                    with csv_path.open() as stream:
                        metrics = list(csv.DictReader(stream))
                    assert len(metrics) == 1
                    metrics = metrics[0]
                    assert metrics['status'] == 'PASS' and int(metrics['event_count']) == len(coordinates)
                    assert int(metrics['flip_count']) == common['scheduled_flips'] and int(metrics['post_branches']) == H
                    assert int(metrics['net']) == int(metrics['harm'])-int(metrics['help']) == int(metrics['faulty_misses'])-int(metrics['clean_misses'])
                    assert math.isclose(float(metrics['delta_MPKI']), 1000*int(metrics['net'])/int(metrics['instructions']), rel_tol=1e-12, abs_tol=1e-12)
                    events_path = Path(str(prefix)+'.events.csv')
                    with events_path.open() as stream:
                        applied = list(csv.DictReader(stream))
                    assert len(applied) == len(coordinates)
                    for row, (t, ids) in zip(applied, events[mapping]):
                        assert float(row['coordinate']) == t and list(map(int, row['site_ids'].split(';'))) == ids
                    record.update(status='PASS', metrics=metrics, CSV=str(csv_path.relative_to(ROOT)),
                        CSV_sha256=sha(csv_path), events_CSV=str(events_path.relative_to(ROOT)), events_CSV_sha256=sha(events_path))
                except Exception as error:
                    record.update(status='FAIL_VALIDATION', error=str(error))
                output.append(record)
        return output

    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=c['workers']) as pool:
        for batch in pool.map(run, jobs):
            results += batch
            print(json.dumps({'completed': len(results), 'failed': sum(r['status'] != 'PASS' for r in results)}), flush=True)
    failed = [r for r in results if r['status'] != 'PASS']
    report = {'status': 'FAIL_EXECUTION_OR_VALIDATION' if failed else 'PASS_CONDITIONAL_FOOTPRINT_PILOT' if args.phase == 'pilot' else 'PASS_FIXED_CONDITIONAL_FOOTPRINT_STRESS',
        'phase': args.phase, 'planned_trials': expected, 'successful_trials': expected-len(failed),
        'failures': failed, 'tasks': results, 'config_sha256': sha(CONFIG), 'binary_sha256': sha(binary),
        'source_model_card_sha256': sha(card_path), 'runner_sha256': sha(Path(__file__)),
        'mapping_manifest_sha256': sha(mapping_path), 'wall_seconds': time.perf_counter()-started,
        'projected_main_serial_seconds': sum(r.get('wall_seconds', 0) for r in results)/len(results)*c['main_trials'],
        'physical_rate_or_mapping_verified': False, 'source_catalog_complete_for_P_MCU': False}
    report_path.write_text(json.dumps(report, indent=2)+'\n')
    if failed:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
