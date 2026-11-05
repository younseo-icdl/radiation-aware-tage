"""Add interpretation/history to a sealed analysis snapshot without resampling."""
import collections
import hashlib
import io
import json
import pathlib
import statistics
import sys
import zipfile

sys.dont_write_bytecode = True
B = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(B / 'continuation_b4/tools'))
import resources as r


def js(x):
    return (json.dumps(x, ensure_ascii=False, indent=2) + '\n').encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def main():
    base = B / 'handoff_analysis/20261018_results_A1'
    prior = next(base.glob('*.zip'))
    out = B / 'handoff_analysis/20261018_results_A2'
    assert not out.exists()
    with zipfile.ZipFile(prior) as z:
        assert z.testzip() is None
        payload = {n: z.read(n) for n in z.namelist()}
    index = json.loads(payload.pop('SHA256_MANIFEST.json'))['files']
    assert set(index) == set(payload)
    assert all(sha(payload[n]) == x['sha256'] and len(payload[n]) == x['bytes'] for n, x in index.items())
    status = json.loads(payload['SNAPSHOT_STATUS.json'])
    analysis = json.loads(payload['data/B4_DEV_SNAPSHOT_ANALYSIS.json'])
    closed = json.loads(payload['data/CLOSED_EXECUTION_RECORDS.json'])
    lookup = {(x['phase'], x.get('program'), x.get('method'), x.get('task', {}).get('scenario'), x.get('task', {}).get('owner')): x for x in closed if x['label'].startswith('B4.')}
    valid_count = 0
    for row in analysis['paired_rows']:
        if not row['valid_pair']:
            continue
        program, method, scenario, owner = (row[k] for k in ('program', 'method', 'scenario', 'owner'))
        keys = (('B4_DEV_CLEAN', program, 'P0', None, None), ('B4_DEV_FAULT', program, 'P0', scenario, owner), ('B4_DEV_CLEAN', program, method, None, None), ('B4_DEV_FAULT', program, method, scenario, owner))
        assert [lookup[k]['cycles'] for k in keys] == [row[k] for k in 'ABCD']
        assert all(lookup[k]['status'].startswith('PASS') for k in keys)
        assert row['net_cycles'] == row['B'] - row['D']
        assert abs(row['net_pct_A'] - 100 * (row['B'] - row['D']) / row['A']) < 1e-12
        assert row['clean_overhead'] == row['C'] - row['A']
        assert row['residual_damage'] == row['D'] - row['C']
        valid_count += 1
    for summary in analysis['paired_summaries']:
        rows = [x for x in analysis['paired_rows'] if x['valid_pair'] and all(x[k] == summary[k] for k in ('program', 'scenario', 'method'))]
        assert len(rows) == summary['valid_pairs']
        if rows:
            assert statistics.mean(x['net_cycles'] for x in rows) == summary['mean_B_minus_D']
            assert abs(statistics.mean(x['net_pct_A'] for x in rows) - summary['mean_net_pct_A']) < 1e-12
    payload['provenance/INDEPENDENT_ABCD_RECOMPUTATION.json'] = js({'status': 'PASS_FROM_FROZEN_EXECUTION_CYCLES_WITHOUT_ANALYZE_MODULE', 'valid_DEV_pairs_checked': valid_count, 'summary_cells_checked': len(analysis['paired_summaries']), 'snapshot_UTC': status['closed_set_captured_UTC'], 'new_CPU': 0})
    sources = json.loads(payload['provenance/ORIGINAL_FILES.json'])
    history = json.loads(payload['history/INDEX.json'])
    extra = [
        ('causal_H1', '/home/youns/workspace/ele548-project-v9/continuation/runtime', 'reports/G1_CAUSAL_REPORT.ko.md'),
        ('causal_H1', '/home/youns/workspace/ele548-project-v9/continuation/runtime', 'reports/CAUSAL_CLAIMS.json'),
        ('causal_H1', '/home/youns/workspace/ele548-project-v9/continuation/runtime', 'reports/CPU_DESIGN_SUMMARY.json'),
        ('causal_H1', '/home/youns/workspace/ele548-project-v9/continuation/runtime', 'reports/CPU_HOLDOUT_SUMMARY.json'),
        ('rate_state_v5', '/home/youns/workspace/ele548-project-v9/rate_state_v5/results', 'FINAL_DECISION.ko.md'),
        ('rate_state_v5', '/home/youns/workspace/ele548-project-v9/rate_state_v5/results', 'NOVELTY_EVIDENCE_MATRIX.md'),
        ('v9_R1', '/home/youns/workspace/ele548-project-v9/rate_state_v9/results', 'FINAL_REPORT.ko.md'),
        ('v11_overwrite', '/home/youns/workspace/ele548-project-v11/overwrite_v11', 'reports/FAULT12_FINAL_REPORT.ko.md'),
        ('v11_overwrite', '/home/youns/workspace/ele548-project-v11/overwrite_v11', 'reports/FAULT12_FINAL_GATES.json'),
    ]
    for label, root, rel in extra:
        path = pathlib.Path(root) / rel
        data = path.read_bytes()
        name = 'history/' + label + '/' + rel
        assert name not in payload
        payload[name] = data
        ref = {'archive_path': name, 'original_path': str(path), 'sha256': sha(data), 'bytes': len(data)}
        sources.append(ref)
        history.append({**ref, 'cohort': label, 'status': 'PRESERVED_OLDER_PRODUCER_NOT_NEW_B4_RESULT'})
    payload['history/INDEX.json'] = js(history)
    payload['provenance/ORIGINAL_FILES.json'] = js(sources)
    payload['PROGRAM_FINDINGS.ko.md'] = '''# 고정된 최신 개발 결과를 읽는 핵심 포인트

아래는 A1의 2026-10-18 05:10 UTC(01:10 EDT) 닫힌 record 집합을 그대로 분석한 것이다. 이후 결과를 추가하지 않았고 CPU 실행/재추첨0이다. B4 DEV qsort34개는 세 scenario×2owner가 모두 끝났지만 dijkstra/SHA 오류 결과는 이 snapshot에 없다. 세 프로그램 정상18개는 모두 있다. 따라서 최신 오류 순위는 qsort 개발 범위에 한정된다.

## 1. qsort SOURCE 반복 오류: 모든 후보가 이득, 전체 승자는 아직 없음

|방법|mean B−D cycles|mean net (% of finite A)|
|---|---:|---:|
|frequent P_ED|584,404.5|4.801148|
|periodic N1-style k64|585,897.5|4.813414|
|SECDED|600,330.5|4.931988|
|TMR|601,941.5|4.945223|
|Exact Direct|593,417|4.875190|

여기서는 TMR의 평균 cycles가 가장 작지만 owner2의 개발 자료이고 물리 비용을 측정하지 않았다. Direct가 conventional 전체를 이겼다는 결과도 아니다. 기존 periodic N1와의 차이는 같은 owner로 판단해야 하며 표의 후보 평균을 독립 표본으로 세지 않는다.

owner0에서 P0 B=13,212,504와 A=12,172,182이므로 피해1,040,322cycles다. ECC D=12,175,291, B−D=1,037,213. owner1의 P0 피해는163,561cycles에 불과했고 ECC B−D=163,448이었다. 두 사건 집합의 효과 크기가 크게 다르다. 평균 이득4.93%만으로 다른 입력/owner에 대한 보편적 효과를 주장할 수 없다.

owner0에서 P0는18events, ECC/Direct는17events를 실제 적용했다. 이는 종료 시각에 따른 사전 선언 first-exit censoring이며 적용 사건 수를 맞추려고 tape를 바꾸지 않았다. SOURCE는2000events/s의 가정 stress다. 측정 target per-bit rate나 mission FIT가 아니다.

## 2. qsort 단일 S* 오류: 한 owner는 CPU 피해0

두 owner 중 하나는 P0/모든 후보의 cycles 변화가0이었다. 다른 owner의 P0 피해2557cycles를 ECC/TMR은 관측상 제거했고 frequent/periodic parity는 각각5/1cycles 잔류했다. ECC/TMR의 평균 B−D=1278.5cycles, A의0.010503%다. zero-impact owner를 제거하지 않았으므로 평균은 피해 owner의 절반이다. Helpful·0·오류 후 상태 discrepancy는 서로 다른 판정이다.

## 3. qsort WHOLE: net0은 오류가 없다는 뜻이 아님

두 WHOLE owner에서 모든 후보의 cycles는 같은 owner P0와 같았다. 따라서 B−D=0이었다. 그러나 B−A는 각각8096/2404cycles로 실제 양수였다. 추가 storage를 포함한 전체 predictor 노출에서 S*만 보호하는 후보들이 이 관측 피해를 줄이지 못했다는 뜻이다. 어느 bit가 그 피해를 만들었는지는 이 표만으로 인과적으로 정할 수 없다. 0을 동등성/안전성으로 부르지 않는다. Direct는 thinning/종료 때문에 owner별 적용 event가30/24, P0는30/25였으며 이를 숨기지 않는다.

## 4. dijkstra와 SHA: 최신 오류 결과는 아직 없음

정상 B4 pipeline은 보존 B2 serial보다 dijkstra5.5735%, SHA1.1071% cycles가 적다. 그러나 native 정상 대비는 각각56.7418%/17.6099% 크다. qsort는 serial 대비12.3049% 감소지만 native 대비123.9176% 증가다. 현재 유한 경로 자체의 정상 비용이 큰 상황에서 finite P0 대비 복구 이득만으로 절대 배포 이득을 주장할 수 없다. Native matched-fault B는 아직 없다.

과거 v9R2/v10에서 Direct와ECC/TMR이 dijkstra/SHA에 같은 cycles를 보인 조건이 있어도 현재 B4의 미실행 값을 대신할 수 없다. 과거 자료는 입력·source/update/service 계약이 다르다.

## 5. 과거 P/N1/H1 결과를 최신 Direct와 구분하기

H1은 보호된 원본/actual-commit shadow와 folded 관계 검증·재구성 방향의 이전 설계다. Fixed-stream golden-assisted HF 개입은 source만 복구하기보다 fold/source 관계를 같이 복구할 때 장기 prediction 피해가 감소함을 보였다. 이 원인 진단은 실제 controller가 아니고 CPU 성능 결과로 발표할 수 없다. `history/causal_H1`은 이 진단과 실제 CPU 비용 비교를 구분해 보존한다.

v3의 `V3_P`는 periodic parity k64에 단계적 복귀(STAGED)를 결합한 후보이고 N1은 periodic parity k64 기준선이다. P와 Exact Direct는 같은 후보가 아니다. v3에서 P/N1의 정상 cycles는 같았지만 P−N1 추가 이득은 작거나 음수이고 주요 CI가0을 포함했다. C++에서 prediction 피해 감소가 보였다는 사실만으로 CPU cycles 우위는 따라오지 않았다. 이후 rate/state v5의 Exact Direct/sparse는 별도 후보이며 v5 READ1/READ2는 single-pending latency sensitivity다. 실제 pipeline의 탈락 근거로 일반화하지 않는다.

이후 v9L0/C0와 v10R8의 결과는 낮은 가정 정상 비용 아래 장기 피해·K2를 다룬다. 현재 B4는 finite port/queue/sampling/commit 비용을 넣은 또 다른 계약이다. 과거의 정상 가정0과 최신 공통 no-op stage를 동일하게 취급하지 않는다.

## 당장 ChatGPT와 논의할 결정

현재 근거는 “Direct가 우승했다”가 아니라 “공통 finite 경로의 정상 비용을 보존하면서 recovery 이득을 비교할 준비가 되었고 qsort개발에서 일부 복구 이득을 확인했다”다. 먼저 동결한 DEV/독립 EVAL을 완료하고, native-fault 대조와 정상 source/commit ordering 비용의 원인 분리를 어디까지 추가할지 판단하는 것이 다음 결정이다. 새 장치/포트 아이디어는 가설로 명시하고 C++gate→작은pilot→gem5순서로 검증한다. RTL/Cadence/SPICE/TCAD는 이번에 실행하지 않는다.
'''.encode()
    # Check every hand-entered interpretation number against the captured records.
    expected = {'P_ED_FREQUENT': 584404.5, 'P_ED_PERIODIC_N1': 585897.5, 'P_ECC': 600330.5, 'P_TMR': 601941.5, 'EXACT_DIRECT': 593417}
    for method, value in expected.items():
        cell = next(x for x in analysis['paired_summaries'] if x['program'] == 'qsort_small' and x['scenario'] == 'SOURCE_RAW130_CHARM_2000S' and x['method'] == method)
        assert cell['mean_B_minus_D'] == value and cell['valid_pairs'] == 2
    whole = [x for x in analysis['paired_rows'] if x['scenario'].startswith('WHOLE') and x['method'] == 'P0']
    assert [x['B'] - x['A'] for x in whole] == [8096, 2404]
    single = [x for x in analysis['paired_rows'] if x['scenario'] == 'SSTAR346_SINGLE_SBU' and x['method'] == 'P0']
    assert [x['B'] - x['A'] for x in single] == [0, 2557]
    payload['README_FIRST.ko.md'] += '\n최신 qsort의 조건별 해석과 과거 H1/P/N1/Direct의 관계는 `PROGRAM_FINDINGS.ko.md`를 함께 읽는다. A2는 A1의 닫힌 집합을 유지하고 설명·과거 근거만 보강했으며 새 실험 결과를 추가하지 않았다.\n'.encode()
    payload['CHATGPT_PROMPT.ko.md'] += '\nPROGRAM_FINDINGS.ko.md도 읽어줘. 최신 qsort WHOLE의 B−D=0에도 B−A>0이었고, P(STAGED)와 Exact Direct는 다른 후보라는 점을 보존해줘.\n'.encode()
    payload['tools/augment_results.py'] = pathlib.Path(__file__).read_bytes()
    payload['provenance/A2_DERIVATION.json'] = js({'source_archive': str(prior), 'source_sha256': r.sha(prior), 'source_closed_capture_UTC': status['closed_set_captured_UTC'], 'new_execution_records_added': 0, 'new_CPU': 0, 'changed_scope': 'Interpretation and historical evidence only; original closed raw bytes preserved', 'original_reporter_setup_errors': ['Initial import lacked root tools path; fixed before capture.', 'Legacy diagnostic/native schemas omit identity fields; only label/phase/program derived from immutable marker/task in aggregate; original raw preserved.'], 'not_simulator_failures': True})
    payload['SHA256_MANIFEST.json'] = js({'algorithm': 'sha256', 'self_excluded': 'SHA256_MANIFEST.json', 'files': {n: {'sha256': sha(d), 'bytes': len(d)} for n, d in sorted(payload.items())}})
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for n, d in sorted(payload.items()):
            z.writestr(n, d)
    data = memory.getvalue()
    r.snapshot(extra_MiB=len(data) / 1048576 + 1)
    out.mkdir()
    artifact = out / 'BP_SEU_Results_ChatGPT_20261018.zip'
    with artifact.open('xb') as f:
        f.write(data)
    for name in ('README_FIRST.ko.md', 'CHATGPT_PROMPT.ko.md', 'RESULTS_AND_ANALYSIS.ko.md', 'PROGRAM_FINDINGS.ko.md', 'SNAPSHOT_STATUS.json'):
        (out / name).write_bytes(payload[name])
    with zipfile.ZipFile(artifact) as z:
        assert z.testzip() is None
        refs = json.loads(z.read('SHA256_MANIFEST.json'))['files']
        assert len(z.namelist()) == len(set(z.namelist())) == len(refs) + 1
        for n, x in refs.items():
            d = z.read(n)
            assert sha(d) == x['sha256'] and len(d) == x['bytes']
    result = {'status': 'PASS_ALL_MEMBER_CRC_SHA256_AND_INDEPENDENT_ABCD_ARITHMETIC', 'artifact': str(artifact), 'sha256': sha(data), 'bytes': len(data), 'members': len(payload), 'snapshot_UTC': status['closed_set_captured_UTC'], 'valid_DEV_pairs_recomputed': valid_count, 'raw_hash_checks_carried_from_A1': status['raw_hash_checks'], 'new_CPU': 0, 'resource_after': r.snapshot()}
    (out / 'PACKAGE_VERIFICATION.json').write_bytes(js(result))
    print(json.dumps({k: result[k] for k in ('status', 'artifact', 'sha256', 'bytes', 'members', 'valid_DEV_pairs_recomputed', 'new_CPU')}, indent=2))


if __name__ == '__main__':
    main()
