#!/usr/bin/env python3
"""Requirement-level evidence audit; incomplete CPU phases never imply completion."""
import collections
import csv
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

from parse_cern_clusters import parse
from summarize_e3_cpu import audit as audit_cpu, sha

ROOT = Path(__file__).resolve().parents[1]
FROZEN = 'dec5020e5a504d0cdf49589e0acc4d2f7e8aa6c61798f61685b468d6dfdefe7b'


def read(path):
    return json.loads((ROOT/path).read_text())


def csv_rows(path):
    with (ROOT/path).open() as stream:
        return list(csv.DictReader(stream))


def evidence(check, paths, **details):
    return {'check': check, 'evidence_sha256': {p: sha(ROOT/p) for p in paths}, **details}


def audit_trials(stage, report_file, config_file, count):
    report, config = read(report_file), read(config_file)
    assert 'PASS' in report['status'] and not report['failures']
    assert report['config_sha256'] == sha(ROOT/config_file)
    assert report['planned_trials'] == report['successful_trials'] == count
    assert report['binary_sha256'] == sha(ROOT/f'build/{stage.lower()}_campaign')
    assert config['rng_namespace_version'] == 2
    assert report['trial_CSV_sha256'] == sha(ROOT/report['trial_CSV'])
    rows = csv_rows(report['trial_CSV'])
    assert len(rows) == count
    stream_owners = {}
    scope = read('sources/protection_scope.lock.json')
    selected_by_field = {field: {site for word in scope['payload_words']
                                if field == '6' or word['word_id'].startswith('raw_path' if field == '4' else 'folded')
                                for site in word['site_ids']} for field in ['4', '5', '6']}
    for row in rows:
        assert row['status'] == 'PASS' and int(row['post_branches']) == 100000
        assert int(row['net']) == int(row['harm'])-int(row['help']) == int(row['faulty_misses'])-int(row['clean_misses'])
        assert int(row['instructions']) > 0
        assert math.isclose(float(row['delta_MPKI']), 1000*int(row['net'])/int(row['instructions']), rel_tol=1e-12, abs_tol=1e-12)
        master = int(row['trial_master_seed'])
        for name, role in [('time_seed', 1), ('k_seed', 2), ('location_seed', 3)]:
            value = int(row[name])
            assert value == (master << 8) | role
            assert value not in stream_owners or stream_owners[value] == (master, role)
            stream_owners[value] = (master, role)
    for task in report['tasks']:
        assert task['status'] == 'PASS' and task['CSV_sha256'] == sha(ROOT/task['output'])
        if stage == 'E1':
            continue
        assert task['event_CSV_sha256'] == sha(ROOT/task['event_CSV'])
        results = csv_rows(task['output'])
        limits = {(r['scheme'], r['trial']): int(r['exposed_bits']) for r in results}
        signatures = collections.defaultdict(list)
        flips = collections.Counter()
        for row in csv_rows(task['event_CSV']):
            key = (row['scheme'], row['trial'])
            sites = list(map(int, row['event_site_ids'].split(';')))
            assert len(sites) == len(set(sites)) == int(row['multiplicity'])
            # selected_payload uses global core IDs, not a 346-bit local index.
            bound = 65370 if results[0]['population'] == 'selected_payload' else limits[key]
            assert all(0 <= site < bound for site in sites)
            assert 0 <= float(row['arrival_conditional_coordinate']) < 100000
            assert 0 <= int(row['applied_before_conditional']) < 100000
            signatures[key].append((row['arrival_conditional_coordinate'], row['event_site_ids']))
            flips[key] += len(sites)
        for row in results:
            key = (row['scheme'], row['trial'])
            assert int(row['event_count']) == len(signatures[key]) and int(row['flip_count']) == flips[key]
            if row['population'] != 'storage_scaled_full':
                assert signatures[key] == signatures[('P0', row['trial'])]
            if row['population'] == 'selected_payload':
                for _, encoded in signatures[key]:
                    assert set(map(int, encoded.split(';'))) <= selected_by_field[row['field']]
            if row['mode'] == 'repeat' and row['model'] != 'ZERO':
                mean_k = (int(task['command'][8])+2*int(task['command'][9]))/(int(task['command'][8])+int(task['command'][9]))
                base_rate = float(task['command'][14])
                normal = row['model'].split('__')[-1]
                normalized = base_rate*mean_k if normal == 'equal_expected_flip' else base_rate
                assert any(math.isclose(normalized, rate, rel_tol=1e-12) for rate in config['base_event_rates_per_conditional'])
                scale = int(row['exposed_bits'])/65370 if row['population'] == 'storage_scaled_full' else 1
                assert math.isclose(float(row['event_rate_per_conditional']), base_rate*scale, rel_tol=1e-12)
                assert math.isclose(float(row['expected_flip_rate_per_conditional']), base_rate*scale*mean_k, rel_tol=1e-12)
    return evidence('PASS_ACTUAL_FIXED_TRIALS_AND_NAMESPACE_AND_ACCOUNTING',
        [report_file, config_file, report['trial_CSV']], trials=count, unique_rng_owners=len(stream_owners))


def main():
    checks = {}
    originals = read('sources/source_manifest.json')
    for item in originals:
        assert sha(ROOT/item['path']) == item['sha256']
    for name in ['tage.cc', 'tage.hh', 'tage_base.cc', 'tage_base.hh']:
        rel = 'src/cpu/pred/'+name
        original = subprocess.check_output(['git', '-C', str(ROOT/'third_party/gem5'), 'show',
            'c8222cc67a399bfc01e8658dd14b30d5bfd634f9:'+rel])
        assert (ROOT/'third_party/gem5-e3'/rel).read_bytes() == original
    assert sha(ROOT/'sources/protection_scope.lock.json') == FROZEN
    scope = read('sources/protection_scope.lock.json')
    assert set(scope['selected_fields']) == {'raw_path', 'folded'} and scope['payload_bits'] == 346
    ids = [site for word in scope['payload_words'] for site in word['site_ids']]
    assert len(ids) == len(set(ids)) == 346
    checks['E0_source_scope'] = evidence('PASS_ORIGINAL_SOURCES_PINNED_ALGORITHM_FROZEN_LOGICAL_SCOPE',
        ['sources/source_manifest.json', 'sources/protection_scope.lock.json', 'reports/E3_INTEGRATION_GATE.json'],
        original_files=len(originals), default_TAGE_algorithm_unchanged=True)

    flying = ROOT/'data/raw/flying_laptop/DetectedSEUTimeTags_with_TLE_Data.csv'
    assert sha(flying) == '94ca982785ec072d36a1c4bdab9c91d220ab6dd9a1ba252b148da91dbb347a46'
    with flying.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    complete = {tuple(row.items()) for row in rows}
    timestamps = {row['Timestamp (ms UTC Unix)'] for row in rows}
    assert (len(rows), len(complete), len(timestamps), len(rows)-len(complete)) == (2129, 2055, 2055, 74)
    provider = read('data/manifests/cern_files.json')
    expected = {r['name']: r['md5'] for r in provider['files']}
    counts = []
    for name, count in [('clust_p29MeV.txt', 1165), ('clust_p0.9MeV.txt', 7456), ('clust_Ar1050MeV.txt', 638)]:
        raw = (ROOT/'data/raw/cern'/name).read_bytes()
        assert hashlib.md5(raw, usedforsecurity=False).hexdigest() == expected[name]
        assert len(parse(raw.decode())) == count
        counts.append(count)
    checks['data'] = evidence('PASS_RECOMPUTED_ORIGINAL_ROWS_DUPLICATES_CERN_MD5_FULL_PARSE',
        ['data/curated/cern_footprint_model_card.json', 'sources/cern_methods.lock.json'],
        Flying_raw=2129, distinct=2055, duplicate_extras=74, CERN_records=counts,
        physical_rate_calibrated=False, independent_particle_identity_verified=False)
    methods = read('sources/cern_methods.lock.json')
    for paper in methods['papers']:
        assert sha(ROOT/paper['path']) == paper['sha256']
    addendum_path = methods['review_addendum']['path']
    assert sha(ROOT/addendum_path) == methods['review_addendum']['sha256']
    addendum = read(addendum_path)
    assert addendum['complete_2014_2015_article_review']
    frozen_card = addendum['frozen_campaign_card']
    assert sha(ROOT/frozen_card['path']) == frozen_card['sha256'] == methods['method_card_sha256']
    assert not addendum['file_specific_clustering_parameters_verified']
    assert not addendum['physical_rate_calibrated'] and not addendum['physical_mapping_verified']
    for paper in addendum['added_papers']:
        assert sha(ROOT/paper['extracted_text']) == paper['extracted_text_sha256']
    for path, digest in addendum['reviewed_images'].items():
        assert sha(ROOT/path) == digest
    checks['CERN_primary_review'] = evidence('PASS_SUPPLIED_PRIMARY_ARTICLES_FROZEN_CAMPAIGN_CARD_PRESERVED',
        ['sources/cern_methods.lock.json', addendum_path, 'reports/CERN_METHOD_REVIEW.ko.md'],
        standalone_2014_2015_review_complete=True, dataset_specific_thresholds_verified=False)

    windows = read('reports/E1_WORKLOAD_WINDOWS.json')
    for item in windows['workloads']:
        design, holdout = item['split_files']['design'], item['split_files']['holdout']
        for window in [design, holdout]:
            assert sha(ROOT/window['path']) == window['sha256']
        assert design['first_last_inclusive_original_record'][1] < holdout['first_last_inclusive_original_record'][0]
    checks['E1'] = audit_trials('E1', 'reports/E1_CAMPAIGN.json', 'configs/e1.design.lock.json', 5760)
    e1 = read('reports/E1_SUMMARY.json')
    assert e1['namespace_correction']['frozen_scope_preserved']
    assert e1['selection']['scope_sha256'] == FROZEN
    checks['E1']['design_holdout_byte_hashes_and_original_intervals'] = 'PASS_6_WORKLOADS'
    checks['E2'] = audit_trials('E2', 'reports/E2_CAMPAIGN.json', 'configs/e2.holdout.lock.json', 8184)
    e2 = read('sources/e2_protection_logical_manifest.json')
    assert e2['same_scope_match'] == 'PASS_ALL_FOUR_346_BITS_23_WORDS'
    assert e2['total_bits'] == {'P0': 65370, 'P_ED': 65433, 'P_ECC': 65531, 'P_TMR': 66062}

    for name, n, config in [('FLYING_TIMING', 2880, 'flying_timing'), ('CERN_FOOTPRINT', 8640, 'cern_footprint')]:
        campaign_file, summary_file = f'reports/{name}_MAIN.json', f'reports/{name}_SUMMARY.json'
        report, summary = read(campaign_file), read(summary_file)
        assert report['successful_trials'] == n and not report['failures']
        assert summary['campaign_sha256'] == sha(ROOT/campaign_file)
        assert summary['config_sha256'] == report['config_sha256'] == sha(ROOT/f'configs/{config}.lock.json')
        assert read(f'configs/{config}.lock.json')['rng_namespace_version'] == 2
        for task in report['tasks']:
            assert task['status'] == 'PASS' and task['CSV_sha256'] == sha(ROOT/task['CSV'])
            assert task['metrics']['status'] == 'PASS'
            assert int(task['metrics']['post_branches']) == 100000
            event_path = task.get('events_CSV', str(Path(task['CSV']).with_suffix('.events.csv')))
            event_hash = task.get('events_CSV_sha256')
            assert event_hash == sha(ROOT/event_path)
            events = csv_rows(event_path)
            assert len(events) == int(task['metrics']['event_count'])
            flips = 0
            for event in events:
                sites = list(map(int, event['site_ids'].split(';')))
                assert len(sites) == len(set(sites)) == int(event['multiplicity'])
                assert set(sites) <= set(ids)
                flips += len(sites)
            assert flips == int(task['metrics']['flip_count'])
        checks[name] = evidence('PASS_FIXED_NAMESPACE_V2_INPUT_AND_RAW_TRIAL_HASHES', [campaign_file, summary_file], trials=n)

    cpu_config = read('configs/e3.cpu.lock.json')
    cpu_pending = []
    for phase in ['pilot', 'main', 'latency']:
        path = f'reports/E3_CPU_{phase.upper()}.json'
        if not (ROOT/path).exists():
            checks['CPU_'+phase] = {'check': 'NOT_DONE', 'reason': 'phase report absent'}
            cpu_pending.append(phase)
            continue
        report = read(path)
        if report['status'] == 'RUNNING':
            checks['CPU_'+phase] = {'check': 'RUNNING_NOT_COMPLETE', 'completed': report['completed_runs'],
                'planned': report['planned_runs'], 'observed_failures': sum(t['status'] != 'PASS' for t in report['tasks'])}
            cpu_pending.append(phase)
            continue
        failures = audit_cpu(report, cpu_config, phase)
        checks['CPU_'+phase] = evidence('PASS_COMPLETE_RAW_CPU_AUDIT' if not failures else 'COMPLETE_WITH_RETAINED_FAILURES',
            [path], trials=report['planned_runs'], failures=len(failures))
    for name in ['reports/E3_CPU_REPORT.ko.md', 'reports/e3_cpu/figures/cpu_fault_slowdown.pdf',
                 'reports/e3_cpu/figures/cpu_assumed_latency.pdf']:
        if not (ROOT/name).exists():
            cpu_pending.append(name)
    integration_path = ROOT/'reports/SOFTWARE_INTEGRATION_REPORT.json'
    if integration_path.exists():
        integration = json.loads(integration_path.read_text())
        assert integration['report_sha256'] == sha(ROOT/'reports/SOFTWARE_INTEGRATION_REPORT.ko.md')
        for path, digest in integration['source_summary_hashes'].items():
            assert sha(ROOT/path) == digest
        checks['integration'] = {'check': integration['status'],
                                 'CPU_main_latency_complete': integration['CPU_main_latency_complete']}
        if integration.get('final_evidence_review_complete'):
            review_path = 'reports/SOFTWARE_FINAL_REVIEW.json'
            assert integration['final_review_sha256'] == sha(ROOT/review_path)
            review = read(review_path)
            assert review['status'] == 'PASS_REVIEWED_CADENCE_PRE_SOFTWARE_SCOPE'
            for path, digest in review['reviewed_evidence_sha256'].items():
                assert sha(ROOT/path) == digest
            checks['final_review'] = evidence('PASS_DIRECT_REVIEW_BOUND_TO_ACTUAL_COMPLETED_EVIDENCE', [review_path])
        if not integration['CPU_main_latency_complete']:
            cpu_pending.append('SOFTWARE_INTEGRATION_REPORT_CPU_SECTION')
    else:
        cpu_pending.append('reports/SOFTWARE_INTEGRATION_REPORT.json')
    checks['E4_handoff'] = evidence('FUNCTIONAL_ASSUMED_TIMING_ACTIVITY_CONTRACT_ACTUAL_RTL_DEFERRED',
        ['sources/e4_software_interface_contract.json', 'reports/E4_SOFTWARE_FUNCTIONAL_HANDOFF.ko.md',
         'reports/E4_SOFTWARE_ACTIVITY_EXPORT.json'], actual_PPA_measured=False)
    result = {'status': 'INCOMPLETE_CPU_CAMPAIGNS_OR_FINAL_OUTPUTS' if cpu_pending else 'PASS_SOFTWARE_REQUIRED_EVIDENCE_AUDIT',
        'checks': checks, 'remaining': cpu_pending, 'source_sha256': sha(Path(__file__)),
        'required_final_step': 'completed; actual statistics, figures, source interpretation and integration reviewed' if 'final_review' in checks else
                               'review actual completed CPU/latency statistics, figures and integration report before marking goal complete',
        'Cadence_TCAD_Geant4_TAGE_SC_L_executed': False}
    (ROOT/'reports/SOFTWARE_COMPLETION_AUDIT.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'status': result['status'], 'remaining': cpu_pending}))


if __name__ == '__main__':
    main()
