#!/usr/bin/env python3
"""Verify current inputs; qualify usable model components, not physical rates."""
import hashlib
import json
from pathlib import Path
from parse_cern_clusters import parse

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'data/manifests/cern_files.json').read_text())
listed = {item['name']: item for item in manifest['files']}
review_path = root / 'data/curated/cern_footprint_model_card.json'
review = json.loads(review_path.read_text()) if review_path.exists() else None
expected_counts = {'clust_p29MeV.txt': 1165, 'clust_p0.9MeV.txt': 7456, 'clust_Ar1050MeV.txt': 638}
checks = []
for name, count in expected_counts.items():
    raw = (root / 'data/raw/cern' / name).read_bytes()
    md5 = hashlib.md5(raw, usedforsecurity=False).hexdigest()
    assert md5 == listed[name]['md5'], f'provider MD5 mismatch: {name}'
    clusters = parse(raw.decode())
    assert len(clusters) == count
    checks.append({'file': name, 'provider_MD5': md5, 'sha256': hashlib.sha256(raw).hexdigest(),
                   'full_file_parse': 'PASS', 'records': count,
                   'origin_record_policy': 'retain raw records; sentinel interpretation pending',
                   'physical_grouping_rate_fit': 'NOT_IDENTIFIED_NO_TARGET_RATE_FIT',
                   'conditional_footprint_review': review['status'] if review else 'PENDING_METHOD_REVIEW'})
flying = root / 'data/raw/flying_laptop/DetectedSEUTimeTags_with_TLE_Data.csv'
assert hashlib.sha256(flying.read_bytes()).hexdigest() == '94ca982785ec072d36a1c4bdab9c91d220ab6dd9a1ba252b148da91dbb347a46'
audit = json.loads((root / 'data/derived/flying_laptop_audit.json').read_text())
assert audit['raw_rows'] == 2129 and audit['unique_complete_rows'] == 2055 and audit['exact_duplicate_extra_rows'] == 74
result = {
    'status': 'PASS_CURRENT_INPUTS_NO_NEW_DATASET_REQUIRED_FOR_REPEATED_CHARM_PILOT',
    'date': '2026-10-12', 'CERN': checks,
    'coverage': [
        {'source': 'CHARM L06 Table II', 'usable': 'separate empirical K=1/2 weights for 6T and 8T',
         'not_identified': 'target spatial geometry or stationary target event rate'},
        {'source': 'CERN Zenodo 8314389', 'usable': 'verified coordinate records; primary-author method-family review permits explicitly conditional recorded-K>=2 hypothetical footprint sensitivity' if review else 'verified coordinate records; after method review, condition-specific shape and K>=3 sensitivity',
         'not_identified': 'cluster/sentinel/singleton completeness and target timing/geometry'},
        {'source': 'Flying Laptop DaRUS 443', 'usable': 'ordered detection timestamps and duplicate-policy sensitivity',
         'not_identified': 'live/dead intervals, sensitive-bit population, detection cadence, physical upset grouping/addresses'},
    ],
    'CERN_primary_metadata': {
        'url': 'https://zenodo.org/records/8314389', 'checked': '2026-10-12',
        'device': 'CY62167GE30-45ZXI, commercial 65nm SRAM',
        'internal_ECC': 'disabled for collection', 'irradiation': 'protons and heavy ions',
        'methods_dois': manifest['methods_dois'], 'full_methods_review': 'STANDALONE_ARTICLES_AND_DATASET_PARAMETERS_NOT_ESTABLISHED',
        'method_family_review': review['status'] if review else 'PENDING',
        'method_card_sha256': hashlib.sha256(review_path.read_bytes()).hexdigest() if review else None,
        'access_notes': 'Public JYX author accepted REDW manuscript and Bosser author thesis obtained by ordinary HTTPS GET; thesis pp51-57 reviewed. CERN CDS/HAL access challenge not bypassed. 2014/2015 standalone papers and dataset-specific thresholds remain unverified.' if review else 'Zenodo metadata read; full method review pending.'
    },
    'additional_dataset_required_now': False,
    'optional_extension': 'additional CERN energies/ions only for a defined model-sensitivity question after qualifying the present three files; do not pool conditions',
    'needed_if_absolute_target_rate_is_requested': ['target or justified transferable cell/structure cross sections',
        'specified radiation flux spectrum/environment', 'susceptible bit population and state/technology assumptions',
        'live exposure/detection information for rate inference'],
    'E4_cost_requires_absolute_SEU_rate': False,
    'E4_requirements': 'same selected functional scope/interface, PDK/library/PVT, clocks/loads, reference/RTL equivalence and measured activity',
    'upload_request': None, 'TCAD': 'UNAVAILABLE_EXCLUDED',
}
(root / 'reports/DATASET_READINESS.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({'status': result['status'], 'verified_CERN_files': len(checks),
                  'additional_dataset_required_now': False}, indent=2))
