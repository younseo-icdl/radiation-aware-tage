"""Complete report tables from immutable executed evidence; no simulations/tuning."""
import collections
import json
import shutil
import statistics

import numpy as np

from v3_common import OUT, ROOT, sha, write


def report(name):
    return json.loads((OUT / 'reports' / (name + '.json')).read_text())


assert report('G7_AUDIT')['status'] == 'PASS'
lines = ['# v3 대조 실험과 비용 한계', '',
         '이 문서는 실행이 끝난 원자료만 집계한다. 아래 development·fixed-stream 수치는 '
         '새 CPU 평가와 구분하며, 입력 하나당 owner 반복을 workload 모집단으로 해석하지 않는다.', '']
refs = report('REFERENCE_BASELINE_SENSITIVITY')['rows']
lines += ['## 공통 유한 source interface의 비용', '',
          '동일 development 입력의 즉시 갱신 P0 참고 실행과 유한 RMW endpoint 실행을 대조했다. '
          '이 둘은 resource contract가 다르다. 최종 A/B/C/D의 A는 유한 endpoint P0이며, '
          '그 분모를 즉시 갱신 P0로 바꾸지 않았다.', '',
          '|프로그램|즉시 P0 cycles|유한 P0 cycles|공통 interface 비용 (%)|N1/P 비용 vs 즉시 P0 (%)|',
          '|---|---:|---:|---:|---:|']
for program in sorted({r['program'] for r in refs}):
    p0 = next(r for r in refs if r['program'] == program and r['variant'] == 'P0')
    n1 = next(r for r in refs if r['program'] == program and r['variant'] == 'N1')
    lines.append(f"|{program}|{p0['immediate_P0_cycles']}|{p0['finite_P0_cycles']}|"
                 f"{p0['overhead_vs_immediate_P0_pct']:+.4f}|{n1['overhead_vs_immediate_P0_pct']:+.4f}|")
lines += ['', '따라서 N1/P의 정상 비용이 유한 P0 대비 작다는 관측만으로 '
          '기존 CPU에 공짜로 붙일 수 있다고 결론 내리지 않는다. 이 interface의 ports·metadata '
          '소유권을 실제 하드웨어에서 바인딩해야 한다.', '']

main = report('CPU_EVALUATION_SUMMARY')
lines += ['## 새 CPU 평가: 프로그램별 순이득', '',
          'net = 100(B−D)/A, pp. 각 셀의 95% CI는 해당 고정 입력의 10개 matched owner를 '
          '10,000회 resample한 값이다. 정상 비용의 입력 간 일반화 신뢰구간은 아니다.', '',
          '|프로그램|조건|보호법|net pp|95% CI|', '|---|---|---|---:|---|']
program_rows = []
for row in main['summary']:
    if row['variant'] not in ['N1', 'V3_P']:
        continue
    for program, metrics in row['per_program'].items():
        net = metrics['net_pp']
        program_rows.append(dict(program=program, scenario=row['scenario'], variant=row['variant'], net=net))
        lines.append(f"|{program}|{row['scenario']}|{row['variant']}|{net['mean']:+.4f}|"
                     f"[{net['CI95'][0]:+.4f}, {net['CI95'][1]:+.4f}]|")

lines += ['', '## 동일 자원의 service 민감도', '',
          'B development producer의 입력·k·code·shadow를 유지하고 L/II와 unit 수만 바꿨다. '
          '각 fault 지점은 directed owner 1개이며, 모집단 CI를 제공하지 않는다. '
          'SHARED2와 SPLIT2는 같은 2-unit capacity/arbiter를 가지므로 partition 개선의 증거로 쓰지 않는다.', '',
          '|프로그램|resource|L/II|N1 clean cycles|P clean cycles|D clean cycles|H1 combined clean cycles|',
          '|---|---|---|---:|---:|---:|---:|']
resources = report('B_RESOURCE')['tasks']
design = report('CPU_DESIGN')['tasks']
resource_rows = []
for program in ['qsort_small', 'dijkstra_small', 'sha1']:
    points = [('SHARED2', 1, 1), ('SHARED2', 2, 1), ('SHARED2', 2, 2), ('SHARED1', 1, 1)]
    for resource, latency, ii in points:
        pool = design if (resource, latency, ii) == ('SHARED2', 1, 1) else resources
        selected = {}
        for variant in ['P0', 'N1', 'V3_P', 'V3_D', 'H1_COMBINED']:
            found = [t for t in pool if t['program'] == program and t['id'] == variant
                     and t['scenario'] == 'zero'
                     and (pool is design or (t['resource'], t['L'], t['II']) == (resource, latency, ii))]
            assert len(found) == 1 and found[0]['status'] == 'PASS'
            t = found[0]
            selected[variant] = t['cycles']
            resource_rows.append(dict(program=program, variant=variant, resource=resource,
                                      L=latency, II=ii, cycles=t['cycles'], output=t['output'],
                                      max_hot_queue=t['seu']['max_hot_queue'],
                                      max_shadow_queue=t['seu']['max_shadow_queue'],
                                      retire_blocked_calls=t['seu']['retire_blocked_calls']))
        lines.append(f"|{program}|{resource}|{latency}/{ii}|{selected['N1']}|{selected['V3_P']}|"
                     f"{selected['V3_D']}|{selected['H1_COMBINED']}|")
lines += ['', '결과는 finite L/II·capacity 조건에 의존한다. callback 후 debt만 청구하는 '
          '기존 A의 진단과 completion에서 기능 효과를 공개하는 B/C의 CPU 모델을 동일시하지 않는다. '
          'metadata codec/scoreboard의 조합논리 bandwidth, operand completion-sampling, '
          'detector-time exceptional reset/ECC의 비용 하한 가정은 '
          'RESOURCE_AND_HARDWARE_CONTRACT.md에 명시했다.', '']

windows = report('B_WINDOWS')['tasks']
window_groups = collections.defaultdict(list)
for t in windows:
    assert t['status'] == 'PASS'
    for w in t['windows']:
        assert int(w['right_censored']) == 0
        window_groups[t['scenario'], t['id'], int(w['requested_postevent_conditionals'])].append(int(w['net']))
window_summary = []
lines += ['## 단일 사건 후 fixed-stream 피해 분포', '',
          '기존 HW1에서 얻은 2 trace × 8 development owner다. 값은 golden 대비 추가 오예측 수이며, '
          'golden은 관측용으로만 쓰고 production controller에는 사용하지 않는다. '
          'H1_FUNCTIONAL_REFERENCE는 동기 shadow reference이며 asynchronous D의 CPU 성능이 아니다. '
          'p90/max는 16건의 경험값이며 p99/WCET를 보장하지 않는다.', '',
          '|사건|보호법|사건 후 conditionals|n|mean additional misses|empirical p90|max|',
          '|---|---|---:|---:|---:|---:|---:|']
for key, values in sorted(window_groups.items()):
    scenario, variant, horizon = key
    summary = dict(scenario=scenario, variant=variant, horizon=horizon, n=len(values),
                   mean=statistics.mean(values), p90=float(np.quantile(values, .9)), maximum=max(values))
    window_summary.append(summary)
    lines.append(f"|{scenario}|{variant}|{horizon}|{len(values)}|{summary['mean']:.4f}|"
                 f"{summary['p90']:.2f}|{summary['maximum']}|")

functional = report('B_FUNCTIONAL')['tasks']
delay_rows = []
for scenario in sorted({t['scenario'] for t in functional}):
    for variant in sorted({t['id'] for t in functional}):
        tasks = [t for t in functional if t['scenario'] == scenario and t['id'] == variant]
        observed = [int(t['metrics']['detector_delay_control_updates']) for t in tasks
                    if int(t['metrics']['detector_delay_control_updates']) >= 0]
        delay_rows.append(dict(scenario=scenario, variant=variant, n=len(tasks),
                               detected_owners=len(observed), undetected_owners=len(tasks)-len(observed),
                               empirical_p90=float(np.quantile(observed, .9)) if observed else None,
                               maximum=max(observed) if observed else None))
lines += ['', '검출 delay는 control update 수다. undetected를 0 delay로 대체하지 않았다.', '',
          '|사건|보호법|검출 owner/전체 owner|max observed delay|', '|---|---|---:|---:|']
for row in delay_rows:
    lines.append(f"|{row['scenario']}|{row['variant']}|{row['detected_owners']}/{row['n']}|"
                 f"{row['maximum'] if row['maximum'] is not None else 'undetected'}|")

sources = report('B_SOURCE_REPLAY')['tasks']
groups = collections.defaultdict(list)
for t in sources:
    groups[t['scenario'], t['id']].append(int(t['metrics']['net']))
source_summary = []
lines += ['', '## Source-informed 재시험', '',
          '다음은 새 v3 구현으로 실행했지만 이미 본 v2 입력·event catalog를 재사용한 '
          'development robustness 시험이다. 독립 holdout이라 부르지 않는다. CERN의 recorded '
          'coordinate-count catalog를 독립 particle strike로 간주하지 않으며, '
          'contiguous/interleaved는 가상 logical mapping이다. Flying의 74개 중복 extra row를 '
          'MCU로 취급하지 않는다.', '',
          '|source pattern|보호법|owner n|mean additional misses|empirical max|',
          '|---|---|---:|---:|---:|']
for (scenario, variant), values in sorted(groups.items()):
    summary = dict(scenario=scenario, variant=variant, n=len(values),
                   mean=statistics.mean(values), maximum=max(values))
    source_summary.append(summary)
    lines.append(f"|{scenario}|{variant}|{len(values)}|{summary['mean']:.4f}|{max(values)}|")

lines += ['', '## 동일 source/detector/shadow의 reset vs rebuild: CPU', '',
          'A producer의 동일 owner·schedule·k/source/shadow·기존 service charge를 유지한 추가 대조다. '
          '평균 RESET−REBUILD cycles가 양수이면 이 조건에서 rebuild가 빠르다. C의 새 평가와 구분한다.', '',
          '|프로그램|paired owners|mean RESET−REBUILD cycles|', '|---|---:|---:|']
arows = report('A3_CPU')['tasks']
paired = collections.defaultdict(dict)
for t in arows:
    paired[t['program'], t['owner']][bool(t['reset_recovery'])] = t
cpu_diffs = collections.defaultdict(list)
for (program, owner), group in paired.items():
    assert set(group) == {False, True}
    assert group[False]['schedule_sha256'] == group[True]['schedule_sha256']
    cpu_diffs[program].append(group[True]['cycles'] - group[False]['cycles'])
for program, values in sorted(cpu_diffs.items()):
    lines.append(f'|{program}|{len(values)}|{statistics.mean(values):+.4f}|')

write(OUT / 'reports/DETAIL_ANALYSIS.json', dict(status='ACTUAL_EVIDENCE_ANALYSIS',
      fixed_program_rows=program_rows, resource_points=resource_rows, postevent_windows=window_summary,
      detector_delay=delay_rows, source_development_replay=source_summary,
      matched_A_reset_minus_rebuild={p:dict(n=len(v), mean=statistics.mean(v)) for p,v in cpu_diffs.items()},
      evidence_hashes={n:sha(OUT / 'reports' / (n+'.json')) for n in ['CPU_EVALUATION_SUMMARY',
          'REFERENCE_BASELINE_SENSITIVITY', 'B_RESOURCE', 'B_WINDOWS', 'B_FUNCTIONAL', 'B_SOURCE_REPLAY', 'A3_CPU']}))
(OUT / 'DETAIL_REPORT.ko.md').write_text('\n'.join(lines)+'\n')

# Keep the pre-experiment rejected/deferred hypotheses, adding observed outcomes.
rejected = OUT / 'REJECTED_DESIGNS.md'
initial = rejected.read_text().split('\n## Observed round outcomes')[0]
freeze = json.loads((OUT / 'configs/CANDIDATE_SPEC.lock.json').read_text())
rejection = freeze['rejected_development']['V3_D']
rejected.write_text(initial + '\n## Observed round outcomes\n\n'
    'D had no development correctness failures, but exceeded the predeclared 2% maximum normal '
    'overhead: ' + ', '.join(f'{p} {v:+.4f}%' for p,v in rejection['clean_overhead_pct'].items()) +
    '. The reason for exclusion is cost, not failed native output. It adds766 logical cells versus '
    'the equally provisioned combined H1 control.\n\n'
    'P passed all gates and fresh evaluation, but each primary P-vs-N1 matched-owner CI includes0. '
    'The 22 extra stage-control cells and protocol complexity did not establish an additional CPU '
    'benefit. The sparse comparison is based on mostly no-event owners; it is not evidence of '
    'a workload-general winner. N1 remains the minimal reference, conditional on paid interface '
    'metadata/ports and the resource assumptions.\n\n'
    'The two frozen family hypotheses have completed their round; G7 is the declared stop before '
    'HDL. Next software change needs a new candidate/owner freeze, not tuning on these holdout outcomes.\n')

# Store compact authoritative state/source manifests without altering original manifests.
manifest_dir = OUT / 'sources'
manifest_dir.mkdir(exist_ok=True)
base = ROOT / 'sources/predictor_logical_state_manifest.json'
shutil.copyfile(base, manifest_dir / base.name)
base_meta = json.loads(base.read_text())
site_path = ROOT / base_meta['site_file']
assert sha(site_path) == base_meta['site_file_sha256']
shutil.copyfile(site_path, manifest_dir / 'base_logical_sites.jsonl')
entries = []
for variant in [v['id'] for v in freeze['variants']]:
    t = next(t for t in report('CPU_EVALUATION')['tasks'] if t['id'] == variant and t['scenario'] == 'zero')
    original = ROOT / t['output'] / 'logical_manifest.json'
    destination = manifest_dir / (variant + '.logical_manifest.json')
    shutil.copyfile(original, destination)
    m = json.loads(original.read_text())
    entries.append(dict(variant=variant, phase='frozen corrected C evaluation',
                        path=str(destination.relative_to(ROOT)), sha256=sha(destination),
                        original=str(original.relative_to(ROOT)), total_bits=m['total_bits'],
                        base_bits=m['base_bits'], additional_bits=m['total_bits']-m['base_bits']))
t = next(t for t in design if t['id'] == 'V3_D' and t['scenario'] == 'zero')
original = ROOT / t['output'] / 'logical_manifest.json'
destination = manifest_dir / 'V3_D.development.logical_manifest.json'
shutil.copyfile(original, destination)
entries.append(dict(variant='V3_D', phase='rejected development B', path=str(destination.relative_to(ROOT)),
                    sha256=sha(destination), original=str(original.relative_to(ROOT))))
card = report('DATA_MODEL_CARD')
write(manifest_dir / 'manifest.json', dict(status='AUDITED_ACTUAL_V3_SOURCES_AND_LOGICAL_STATE',
      original_source_manifest=dict(path='sources/manifest.json', sha256=sha(ROOT/'sources/manifest.json')),
      base_logical_sites=dict(path=str((manifest_dir/'base_logical_sites.jsonl').relative_to(ROOT)),
                              sha256=sha(manifest_dir/'base_logical_sites.jsonl'), bits=65370),
      selected_scope=dict(path='sources/protection_scope.lock.json', sha256=sha(ROOT/'sources/protection_scope.lock.json'), bits=346),
      provider_manifest=dict(path='data/manifests/cern_files.json', sha256=sha(ROOT/'data/manifests/cern_files.json')),
      CERN=card['CERN'], FlyingLaptop_source_sha256=card['FlyingLaptop']['source_sha256'],
      per_variant=entries, CPU_interface_exclusion='44 added logical bits per live CpuInfo; assumed protected CPU ownership; storage/ports/lifetime must be paid',
      full_scope_not_full_CPU_radiation_qualification=True, physical_rate_calibrated=False))

final = OUT / 'FINAL_REPORT.ko.md'
body = final.read_text().split('\n詳細な対照表と分布')[0]
final.write_text(body+'\n詳細な対照表と分布は [DETAIL_REPORT.ko.md](DETAIL_REPORT.ko.md)、'
                 '新しいlogical-state/source manifestは [sources/manifest.json](sources/manifest.json) にある。\n')
print('Actual detail tables, rejections and manifests completed; no producer/data/owner changes')
