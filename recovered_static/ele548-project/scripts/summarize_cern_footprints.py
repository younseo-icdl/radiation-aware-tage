#!/usr/bin/env python3
"""Audit and summarize fixed conditional CERN footprint replay."""
import csv
import json
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from parse_cern_clusters import parse
from run_cern_footprints import sha, translations

ROOT = Path(__file__).resolve().parents[1]


def main():
    c = json.loads((ROOT/'configs/cern_footprint.lock.json').read_text())
    path = ROOT/'reports/CERN_FOOTPRINT_MAIN.json'
    report = json.loads(path.read_text())
    assert report['status'] == 'PASS_FIXED_CONDITIONAL_FOOTPRINT_STRESS'
    assert report['successful_trials'] == report['planned_trials'] == c['main_trials']
    assert report['config_sha256'] == sha(ROOT/'configs/cern_footprint.lock.json')
    assert report['binary_sha256'] == sha(ROOT/'build/scheduled')
    assert report['source_model_card_sha256'] == sha(ROOT/'data/curated/cern_footprint_model_card.json')
    mapping_path = ROOT/'sources/cern_hypothetical_mapping_manifest.json'
    assert report['mapping_manifest_sha256'] == sha(mapping_path)
    maps = json.loads(mapping_path.read_text())['mapping_cell_order']
    source = {name: {row['cluster_id']: row for row in parse((ROOT/'data/raw/cern'/name).read_text())}
              for name in c['files']}
    source_anchors = {name: {ident: set(translations(row['offsets_from_anchor']))
                           for ident, row in rows.items() if row['multiplicity_from_unique_coordinates'] >= 2}
                      for name, rows in source.items()}
    shapes = {}
    by = {}
    paired_events = defaultdict(set)
    for t in report['tasks']:
        key = (t['workload'], t['source_file'], t['mode'], t['normalization'], t['mapping'], t['scheme'], t['trial'])
        assert key not in by and t['status'] == 'PASS'
        by[key] = t
        for f, checksum in [('CSV', 'CSV_sha256'), ('events_CSV', 'events_CSV_sha256'),
                            ('schedule', 'schedule_sha256')]:
            assert sha(ROOT/t[f]) == t[checksum], f'{t["log"]}: altered {f}'
        with (ROOT/t['CSV']).open() as stream:
            assert list(csv.DictReader(stream)) == [t['metrics']]
        shape_file = t['shape_manifest']
        if shape_file not in shapes:
            assert sha(ROOT/shape_file) == t['shape_manifest_sha256']
            rows = [json.loads(s) for s in (ROOT/shape_file).read_text().splitlines()]
            for row in rows:
                original = source[t['source_file']][row['source_cluster_id']]
                assert row['K'] == original['multiplicity_from_unique_coordinates'] >= 2
                assert row['source_offsets'] == original['offsets_from_anchor']
                x, y = row['hypothetical_anchor']
                anchors = source_anchors[t['source_file']][row['source_cluster_id']]
                assert (x, y) in anchors and len(anchors) == row['valid_translation_count']
                cells = [(y+dy)*16+x+dx for dx, dy in row['source_offsets']]
                for mapping in c['mappings']:
                    ids = row['logical_sites'][mapping]
                    assert len(ids) == len(set(ids)) == row['K']
                    assert set(ids) <= set(maps[mapping])
                    if mapping != 'dispersed_same_K':
                        assert ids == [maps[mapping][cell] for cell in cells]
            shapes[shape_file] = rows
        rows = shapes[shape_file]
        assert len(rows) == t['scheduled_events'] == int(t['metrics']['event_count'])
        assert sum(row['K'] for row in rows) == t['scheduled_flips'] == int(t['metrics']['flip_count'])
        with (ROOT/t['events_CSV']).open() as stream:
            applied = list(csv.DictReader(stream))
        assert len(applied) == len(rows)
        for row, applied_row in zip(rows, applied):
            assert float(applied_row['coordinate']) == row['coordinate']
            assert list(map(int, applied_row['site_ids'].split(';'))) == row['logical_sites'][t['mapping']]
        paired_events[key[:4]+(t['trial'],)].add((t['shape_manifest_sha256'], t['scheduled_events'], t['scheduled_flips'], t['anchor_phase']))
    assert all(len(values) == 1 for values in paired_events.values())
    assert len(by) == c['main_trials']
    rng = np.random.default_rng(c['bootstrap_seed'])
    groups = []
    for name in c['files']:
        for mode in c['modes']:
            norms = ['equal_event'] if mode == 'single' else c['repeat_normalizations']
            n = c['single_trials_per_condition'] if mode == 'single' else c['repeat_trials_per_condition']
            index = rng.integers(0, n, size=(c['bootstrap_replicates'], len(c['workloads']), n))

            def estimate(values):
                values = np.asarray(values)
                draws = np.stack([values[j, index[:, j, :]].mean(axis=1)
                                  for j in range(len(c['workloads']))], axis=1).mean(axis=1)
                return {'mean': float(values.mean()), 'matched_trial_bootstrap95CI': np.quantile(draws, [.025, .975]).tolist()}

            for norm in norms:
                for mapping in c['mappings']:
                    for scheme in c['schemes']:
                        def values(metric, target=mapping, target_scheme=scheme):
                            return np.array([[float(by[(w, name, mode, norm, target, target_scheme, trial)]['metrics'][metric])
                                              for trial in range(n)] for w in c['workloads']])
                        data = values('delta_MPKI')
                        metrics = {metric: estimate(values(metric)) for metric in
                            ['net', 'harm', 'help', 'end_differing_base_bits', 'detected', 'corrected', 'DUE',
                             'reset_refill', 'fallback_predictions', 'event_count', 'flip_count']}
                        collisions = {}
                        for metric in ['multi_bit_word_events', 'three_plus_same_word_events']:
                            collisions[metric] = estimate([[float(by[(w, name, mode, norm, mapping, scheme, trial)][metric])
                                                           for trial in range(n)] for w in c['workloads']])
                        groups.append({'file': name, 'mode': mode, 'normalization': norm, 'mapping': mapping,
                            'scheme': scheme, 'trials': len(c['workloads'])*n, 'delta_MPKI': estimate(data),
                            'difference_from_word_contiguous': estimate(data-values('delta_MPKI', 'word_contiguous')),
                            'difference_from_dispersed_same_K': estimate(data-values('delta_MPKI', 'dispersed_same_K')),
                            'difference_from_P_ED_same_mapping': estimate(data-values('delta_MPKI', target_scheme='P_ED')),
                            'metrics': metrics, 'word_collision_metrics': collisions})
    result = {'status': 'PASS_AUDITED_CONDITIONAL_CERN_FOOTPRINT_SUMMARY',
        'successful_trials': report['successful_trials'], 'execution_failures': 0,
        'campaign_sha256': sha(path), 'config_sha256': report['config_sha256'],
        'model_card_sha256': report['source_model_card_sha256'], 'analysis_source_sha256': sha(Path(__file__)),
        'audit': 'all raw CSV/event/schedule hashes and source ID/K/offsets/whole-shape bijections checked; paired clocks/source shapes/anchors/K verified',
        'groups': groups, 'physical_rate_or_mapping_verified': False,
        'uncertainty': 'matched-seed bootstrap 2000 within each of six fixed workloads; source catalog fixed, not particle-grouping/completeness/flux/PDK uncertainty',
        'TMR_limit': c['TMR_boundary'], 'rate_model': c['time_model']}
    (ROOT/'reports/CERN_FOOTPRINT_SUMMARY.json').write_text(json.dumps(result, indent=2)+'\n')
    destination = ROOT/'reports/cern_footprints/figures'
    destination.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    x = np.arange(len(c['mappings']))
    for ax, name in zip(axes, c['files']):
        for scheme in c['schemes']:
            rows = [next(g for g in groups if g['file'] == name and g['mode'] == 'repeat'
                         and g['normalization'] == 'equal_event' and g['mapping'] == mapping and g['scheme'] == scheme)
                    for mapping in c['mappings']]
            mean = np.array([g['delta_MPKI']['mean'] for g in rows])
            ci = np.array([g['delta_MPKI']['matched_trial_bootstrap95CI'] for g in rows])
            ax.errorbar(x, mean, yerr=np.maximum(0, np.stack([mean-ci[:, 0], ci[:, 1]-mean])),
                        label=scheme, marker='o', capsize=3)
        ax.set_title(Path(name).stem.replace('clust_', ''))
        ax.set_xticks(x, ['Word contiguous', 'Word interleaved', 'Dispersed K'], rotation=18)
        ax.set_ylabel('Change in MPKI')
        ax.axhline(0, color='gray', lw=.6)
    axes[0].legend(fontsize=8)
    fig.suptitle('Recorded K>=2 catalog conditional stress; hypothetical layout, equal event rate')
    fig.tight_layout()
    for ext in ['pdf', 'png']:
        fig.savefig(destination/f'footprint_sensitivity.{ext}', dpi=180)
    plt.close(fig)
    lines = ['# CERN 기록 군집의 공간 패턴 민감도 — 소프트웨어 결과', '',
        f"고정 holdout {report['successful_trials']} trials를 완료했다. 실행 실패 0. E1에서 동결한 S* 346 bits와 P0/P_ED/P_ECC/P_TMR를 사용했다.", '',
        '원문 검토와 한계는 CERN_METHOD_REVIEW.ko.md 및 data/curated/cern_footprint_model_card.json에 있다. 이 실험은 파일별 기록된 K≥2 군집에 조건화한다. Empirical P(MCU), target per-bit/second 오류율, 물리 layout을 측정한 결과가 아니다.', '',
        '## Repeated equal-event stress (λ=10⁻³/conditional branch)', '',
        '| 기록 조건 | Scheme | Word-contiguous ΔMPKI | Word-interleaved ΔMPKI | Dispersed same-K ΔMPKI | Interleaved−contiguous (95% CI) |',
        '|---|---|---:|---:|---:|---:|']
    for name in c['files']:
        for scheme in c['schemes']:
            rows = [next(g for g in groups if g['file'] == name and g['mode'] == 'repeat'
                         and g['normalization'] == 'equal_event' and g['mapping'] == mapping and g['scheme'] == scheme)
                    for mapping in c['mappings']]
            difference = rows[1]['difference_from_word_contiguous']
            lo, hi = difference['matched_trial_bootstrap95CI']
            lines.append('| '+Path(name).stem+' | '+scheme+' | '+' | '.join(f"{g['delta_MPKI']['mean']:.6g}" for g in rows)
                         +f" | {difference['mean']:.6g} [{lo:.6g}, {hi:.6g}] |")
    lines += ['', 'Single-event 20 seeds/condition와 repeated 10 seeds/condition, equal-event / equal-expected-flip를 모두 실행했다. Equal-flip clock은 λ/E[K|recorded K≥2]이며 두 proton 조건과 Ar 조건을 pooling하지 않았다. 모든 event/K/좌표/translation/site/seed/schedule와 CSV를 보존하고 hash를 대조했다.', '',
        'Matched-seed CI는 6개 고정 holdout workload에 조건화한 bootstrap 2000회다. Branch 수를 독립 표본 수로 쓰지 않는다. 원본 catalog의 grouping 오류, singleton 누락, 물리 배치 불확실성은 이 CI 밖이다. Harm/help/zero를 모두 보존하고 원 instruction denominator로 ΔMPKI를 계산한다.', '',
        '배치는 16×22 가상 논리 tile의 bijection이다. 원본 offsets를 전부 유지하고 유효 translation만 선택한다. Dispersed 대조는 동일 K를 유지하면서 공간적 연결만 제거한다. No wrapping/clipping 또는 K 축소. Extra parity/ECC/control/replica cells는 이번 payload 비교에서 제외하고 E2/E3의 별도 exposure 시험으로 다룬다.', '',
        'TMR는 replica0만 오류에 노출되므로 두 건강한 사본을 유지한다. 이 결과로 실제 replica 간 물리 독립성 또는 전체 CPU 내성을 주장하지 않는다. 이 C++ 시험의 ΔMPKI는 gem5 cycles/IPC나 RTL latency/PPA가 아니다.', '',
        '재현: scripts/qualify_cern_footprints.py → scripts/run_cern_footprints.py --phase pilot/main → scripts/summarize_cern_footprints.py. Config, source-method lock, hypothetical mapping manifest 및 raw logs를 함께 보존한다.']
    (ROOT/'reports/CERN_FOOTPRINT_REPORT.ko.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'status': result['status'], 'successful_trials': result['successful_trials'], 'groups': len(groups)}))


if __name__ == '__main__':
    main()
