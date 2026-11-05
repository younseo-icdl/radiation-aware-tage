#!/usr/bin/env python3
"""Reproduce the frozen campaign card; later paper review is a separate addendum."""
import collections
import hashlib
import json
from pathlib import Path
from parse_cern_clusters import parse

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    papers = [
        {'source_id': 'L08', 'path': 'sources/papers/CERN_2020_SRAM_characterization.pdf',
         'url': 'https://jyx.jyu.fi/bitstreams/e328580f-8d6c-478d-b815-f1b59fa07728/download',
         'doi': '10.1109/REDW51883.2020.9325822', 'version': 'author accepted manuscript with repository cover',
         'reviewed_PDF_pages': [2, 3], 'claim': 'commercial CY62167GE30-45ZXI 65nm, internal ECC disabled by interfacing FPGA; irradiation conditions vary'},
        {'source_id': 'L09', 'path': 'sources/papers/Bosser_2017_thesis.pdf',
         'url': 'https://jyx.jyu.fi/bitstream/handle/123456789/56348/1/A_Bosser_%20Doctoral%20thesis_%20v12_FINAL.pdf',
         'doi': None, 'version': 'author doctoral thesis, 98-page repository PDF',
         'reviewed_PDF_pages': [50, 51, 52, 53, 54, 55, 56, 57],
         'claim': 'TIGER cluster output and spatial/temporal clustering described by the 2015 method author; singleton type A and possible aggregation false positives; physical bitmap requires address scrambling/interleaving information'},
    ]
    for paper in papers:
        path = ROOT/paper['path']
        assert path.read_bytes().startswith(b'%PDF-')
        paper.update(sha256=sha(path), size_bytes=path.stat().st_size)
    manifest = json.loads((ROOT/'data/manifests/cern_files.json').read_text())
    listed = {item['name']: item for item in manifest['files']}
    files = []
    for name in manifest['default_subset']:
        raw = (ROOT/'data/raw/cern'/name).read_bytes()
        assert hashlib.md5(raw, usedforsecurity=False).hexdigest() == listed[name]['md5']
        rows = parse(raw.decode())
        multiple = [r for r in rows if r['multiplicity_from_unique_coordinates'] >= 2]
        histogram = collections.Counter(r['multiplicity_from_unique_coordinates'] for r in multiple)
        files.append({'file': name, 'condition': listed[name]['condition'],
            'provider_MD5': listed[name]['md5'], 'raw_sha256': hashlib.sha256(raw).hexdigest(),
            'raw_records': len(rows), 'conditional_K_ge_2_records': len(multiple),
            'conditional_K_histogram': dict(sorted(histogram.items())),
            'conditional_mean_K': sum(k*n for k, n in histogram.items())/len(multiple),
            'origin_flagged_ids_retained_raw': [r['cluster_id'] for r in rows if r['suspected_origin_sentinel']],
            'shape_offsets_status': 'retained coordinate offsets in provider coordinate units; source geometry to TAGE not measured',
            'full_raw_parse': 'PASS'})
    review = {
        'status': 'QUALIFIED_CONDITIONAL_PROVIDER_CLUSTER_FOOTPRINT_SENSITIVITY',
        'source_access': 'normal public HTTPS GET, no bot-challenge solving/authentication/paywall bypass',
        'additional_papers': papers, 'files': files,
        'source_facts': [
            'Zenodo 8314389 explicitly identifies collected clusters as MCU data and cites the 2014/2015 clustering methods',
            'L09 p51 describes TIGER lists of bit-error structures, cluster bounding coordinates/time ranges and formatted cluster/error output',
            'L09 p57 describes iterative accretion under spatial/temporal proximity criteria, removing sequential type C errors first',
            'L09 p54 includes isolated SBUs in type A; p57 gives an example aggregation false positive',
            'L09 p53 requires precise address scrambling/interleaving for physical bitmap reconstruction; displayed bitmap occupancy is not repeated-upset count',
        ],
        'review_limit': 'method family verified from primary author thesis; 2014/2015 standalone articles remain unavailable. Exact parameterization/output code used for these three 2023 files is not established',
        'not_identified': ['file-specific spatial/temporal grouping thresholds and true-strike identity',
            'singleton completeness / file0 origin record meaning', 'per-file live exposure and flux/fluence suitable for event-rate inference',
            'source coordinate scrambling/physical pitch and target PDK mapping'],
        'qualified_use': 'uniform resampling of recorded K>=2 catalog entries separately per condition, conditional software stress. Preserve every coordinate/K atomically; hypothetical target mapping explicitly labeled',
        'catalog_policy': 'K>=2 is the declared estimand; singleton/origin records remain in original and audit. No empirical P(MCU) from this filtered catalog, no silent sentinel deletion',
        'time_model': 'declared independent Poisson in conditional-branch exposure; not extracted from source clock labels',
        'rate_calibrated': False, 'physical_mapping_verified': False, 'independent_particle_grouping_verified': False,
        'thesis_example_thresholds_transferred_to_dataset': False,
        'complete_2014_2015_article_review': False,
    }
    destination = ROOT/'data/curated/cern_footprint_model_card.json'
    serialized = json.dumps(review, indent=2)+'\n'
    if destination.exists():
        # Completed campaigns bind these exact bytes. Do not rewrite their
        # historical input when a later source review becomes available.
        assert destination.read_text() == serialized, 'frozen campaign card changed'
    else:
        destination.write_text(serialized)
    lock_path = ROOT/'sources/cern_methods.lock.json'
    if lock_path.exists():
        lock = json.loads(lock_path.read_text())
        assert lock['method_card_sha256'] == sha(destination)
        known = {p['source_id']: p for p in lock['papers']}
        for paper in papers:
            assert known[paper['source_id']]['sha256'] == paper['sha256']
        # Preserve supplied-paper provenance and the retrospective addendum.
    else:
        lock_path.write_text(json.dumps({'papers': papers, 'method_card_sha256': sha(destination)}, indent=2)+'\n')
    print(json.dumps({'status': review['status'], 'conditional_records': [f['conditional_K_ge_2_records'] for f in files]}))


if __name__ == '__main__':
    main()
