"""Read-only, closed-record analysis handoff. Never dispatch/rebuild a producer."""
import argparse
import collections
import csv
import datetime as dt
import hashlib
import io
import json
import pathlib
import statistics
import subprocess
import sys
import zipfile

sys.dont_write_bytecode = True
B = pathlib.Path(__file__).resolve().parents[2]
W = B.parent
V9 = pathlib.Path('/home/youns/workspace/ele548-project-v9')
V10 = pathlib.Path('/home/youns/workspace/ele548-project-v10')
V15 = pathlib.Path('/home/youns/workspace/ele548-project-v15/query_controls_v15')
K4 = B / 'runtime/continuation_b4'
sys.path.insert(0, str(B / 'continuation_b4/tools'))
sys.path.insert(1, str(B / 'tools'))
import campaign
import resources as r
import analyze


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def js(obj):
    return (json.dumps(obj, indent=2, ensure_ascii=False) + '\n').encode()


def csv_bytes(rows):
    fields = list(dict.fromkeys(k for row in rows for k in row))
    f = io.StringIO(newline='')
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in row.items()})
    return f.getvalue().encode('utf-8-sig')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--tag', required=True)
    args = ap.parse_args()
    assert args.tag.replace('_', '').replace('-', '').isalnum()
    out = B / 'handoff_analysis' / args.tag
    assert not out.exists(), 'Use a fresh snapshot tag; old snapshots are immutable.'
    started = now()
    payload = {}
    files = []

    def add(name, data):
        assert name not in payload and not name.startswith('/') and '..' not in pathlib.PurePosixPath(name).parts
        payload[name] = data

    def source(path, name, expected=None):
        path = pathlib.Path(path)
        data = path.read_bytes()
        sha = digest(data)
        if expected is not None:
            assert sha == expected, ('SOURCE_HASH_MISMATCH', str(path), expected, sha)
        add(name, data)
        files.append({'archive_path': name, 'original_path': str(path), 'sha256': sha, 'bytes': len(data)})
        return data

    # A finite set of markers is captured once. Each EXECUTION is read once.
    marker_paths = sorted((B / 'runtime/run_starts').glob('*.json'))
    closed, active, frozen_rows = [], [], collections.defaultdict(list)
    raw_verified = 0
    for marker in marker_paths:
        task = json.loads(marker.read_bytes())
        record = pathlib.Path(task['output']) / 'EXECUTION.json'
        if not record.exists():
            active.append(task)
            continue
        raw = record.read_bytes()
        row = json.loads(raw)
        # Legacy native/diagnostic schemas omit identifying fields. Derive only
        # these identities from the immutable start marker, preserving raw bytes.
        derived = {}
        for field in ('label', 'phase'):
            if field not in row:
                derived[field] = task[field]
        if 'program' not in row and 'program' in row.get('task', {}):
            derived['program'] = row['task']['program']
        if derived:
            row = {**derived, **row, 'snapshot_identity_fields_from_marker_or_task': list(derived)}
        closed.append(row)
        label = row['label']
        add('raw_closed/' + label + '/EXECUTION.json', raw)
        files.append({'archive_path': 'raw_closed/' + label + '/EXECUTION.json', 'original_path': str(record), 'sha256': digest(raw), 'bytes': len(raw)})
        for name, expected in row.get('hashes', {}).items():
            source(record.parent / name, 'raw_closed/' + label + '/' + name, expected)
            raw_verified += 1
        if label.startswith('B4.'):
            assert row['phase'].startswith('B4_')
            frozen_rows[row['phase'][3:]].append(row)
        schedule = row.get('task', {}).get('schedule')
        if schedule:
            name = 'schedules/' + pathlib.Path(schedule['path']).name
            if name not in payload:
                source(schedule['path'], name, schedule['sha256'])
    captured = now()
    # Existing analysis is evaluated against the frozen in-memory record set only.
    campaign.rows = lambda phase: frozen_rows.get(phase, [])
    analyses = {}
    for cohort in ('DEV', 'EVAL'):
        x = analyze.summarize(cohort)
        x['snapshot_not_terminal_report'] = True
        x['planned_fault_runs'] = 102 if cohort == 'DEV' else 408
        x['phase_complete'] = x['attempted_faults'] == x['planned_fault_runs'] and x['failure_count'] == 0
        x['CI_reporting_policy'] = 'n=1 CI suppressed; n=2 descriptive exploratory owner bootstrap only; no equivalence or population coverage claim'
        for cell in x['paired_summaries']:
            cell['planned_owners'] = 2 if cohort == 'DEV' else 8
            cell['cell_complete'] = cell['valid_pairs'] == cell['planned_owners']
            cell['inference_status'] = 'DEVELOPMENT_EXPLORATORY' if cohort == 'DEV' else 'INDEPENDENT_INPUT_OWNER_EVALUATION'
            if cell['valid_pairs'] < 2:
                cell['bootstrap95_cycles'] = None
                cell['exact_two_sided_sign_p'] = None
                cell['Holm_sign_p_within_program_scenario'] = None
        analyses[cohort] = x
        add('data/B4_' + cohort + '_SNAPSHOT_ANALYSIS.json', js(x))
        add('data/B4_' + cohort + '_ABCD.csv', csv_bytes(x['paired_rows']))
        add('data/B4_' + cohort + '_PAIRED_SUMMARY.csv', csv_bytes(x['paired_summaries']))
        add('data/B4_' + cohort + '_CLEAN.csv', csv_bytes(x['clean']))

    counters = []
    for row in closed:
        if row['label'].startswith('B4.'):
            counters.append({**{k: row.get(k) for k in ('label', 'phase', 'program', 'method', 'status', 'cycles', 'IPC', 'host_cpu_seconds', 'wall_seconds', 'applied_events', 'applied_flips')}, **{k: row.get('task', {}).get(k) for k in ('owner', 'scenario')}, **row.get('program_exit_seu', {})})
    add('data/B4_ALL_CLOSED_COUNTERS.csv', csv_bytes(counters))
    add('data/CLOSED_EXECUTION_RECORDS.json', js(closed))
    failures = [{'label': x['label'], 'phase': x['phase'], 'program': x.get('program'), 'method': x.get('method'), 'status': x['status'], 'cycles': x.get('cycles'), 'failure': x.get('failure'), 'exit_code': x.get('exit_code'), 'command': x.get('command'), 'raw_archive_path': 'raw_closed/' + x['label'] + '/EXECUTION.json'} for x in closed if x['status'].startswith('FAIL')]
    add('data/RETAINED_EXECUTION_FAILURES.csv', csv_bytes(failures))
    add('data/ACTIVE_AT_CAPTURE_EXCLUDED.json', js({'capture_window': [started, captured], 'tasks': active, 'rule': 'No active output files copied; these are missing results, never zero-impact or failed results.'}))

    counts = collections.Counter((x['phase'], x['status']) for x in closed)
    resource = r.snapshot()
    producer = r.load(B / 'reports/PRODUCER_B4.lock.json')
    verified_dependencies = []
    for ref in [producer['binary'], producer['config'], producer['observer'], producer['source_lock'], *producer['actual_dependencies'], *producer['execution_tools']]:
        assert r.sha(ref['path']) == ref['sha256'], ('PRODUCER_CHANGED', ref)
        verified_dependencies.append(ref)
    original_elf = V15 / 'runtime/gem5_build_A1/gem5.query_early.opt'
    original_sha = 'ffd9d1013f9dc567e84b984dce799626fa3609e276c0b91cddd2d66c4921854c'
    assert r.sha(original_elf) == original_sha
    add('provenance/PRODUCER_INTEGRITY_AT_CAPTURE.json', js({'status': 'PASS_ACTUAL_HASH_VERIFICATION', 'verified_at': now(), 'B4_references': verified_dependencies, 'original_v17_ELF': {'path': str(original_elf), 'sha256': original_sha}, 'ELF_embedded': False, 'not_full_build_closure': True}))

    # Current evidence, immutable historical controls, and review notes.
    for path in sorted((B / 'reports').glob('*')):
        if path.is_file() and path.suffix in ('.json', '.md'):
            source(path, 'evidence/v18_reports/' + path.name)
    for path in sorted((K4 / 'reports').glob('*')):
        if path.is_file() and path.suffix in ('.json', '.md'):
            source(path, 'evidence/B4_reports/' + path.name)
    for path in (B / 'docs/00_LATEST_DECISIONS.ko.md', B / 'docs/02_IMPLEMENTED_RESOURCE_CONTRACT.ko.md', B / 'sources/B4_FAULT_AND_RESOURCE_MODEL_CARD.ko.md', B / 'sources/B4_SOURCE_AND_LOGICAL_MANIFEST.lock.json', W / 'AGENTS.md'):
        source(path, 'contracts/' + path.name)
    # The predictor implementation and gate fixtures are small; no ELF/PDK/input distributions.
    for directory, prefix in ((B / 'producer_source/B4', 'implementation/B4'), (B / 'tests', 'implementation/tests'), (B / 'continuation_b4/tools', 'implementation/B4_experiment_tools')):
        for path in sorted(directory.rglob('*')):
            if path.is_file() and path.suffix in ('.hpp', '.h', '.cc', '.cpp', '.hh', '.py', '.json', '.md') and '__pycache__' not in path.parts:
                source(path, prefix + '/' + path.relative_to(directory).as_posix())
    source(pathlib.Path(__file__), 'tools/build_snapshot.py')
    for method in campaign.METHODS:
        path = B / 'runtime/initialization_B4' / method / 'logical_manifest.json'
        source(path, 'manifests/' + method + '.json')
    for name in ('COHORT_INPUTS.lock.json', 'COHORT_PREREGISTRATION.lock.json'):
        assert 'evidence/B4_reports/' + name in payload
    for path in sorted((K4 / 'runtime/configs').glob('*_PLAN.lock.json')):
        source(path, 'plans/' + path.name)

    history = []

    def historical(label, root, relative):
        for rel in relative:
            path = root / rel
            assert path.exists(), ('MISSING_HISTORICAL_EVIDENCE', str(path))
            name = 'history/' + label + '/' + rel
            source(path, name)
            history.append({'cohort': label, 'archive_path': name, 'original_path': str(path), 'sha256': digest(payload[name]), 'status': 'PRESERVED_OLDER_PRODUCER_NOT_NEW_B4_RESULT'})

    historical('E0_E3_corrected_rng_v2', V9, ['reports/SOFTWARE_FINAL_REVIEW.json', 'reports/E1_SUMMARY.json', 'reports/E2_SUMMARY.json', 'reports/E3_CPU_MAIN_SUMMARY.json', 'reports/E3_CPU_LATENCY_SUMMARY.json', 'reports/E3_CPU_REPORT.ko.md', 'reports/CERN_METHOD_REVIEW.ko.md', 'reports/CERN_FOOTPRINT_SUMMARY.json', 'reports/FLYING_TIMING_SUMMARY.json', 'sources/protection_scope.lock.json', 'sources/cern_methods.lock.json'])
    historical('costaware_v3', V9 / 'continuation_v3/runtime', ['FINAL_REPORT.ko.md', 'DETAIL_REPORT.ko.md', 'CPU_RESULTS_evaluation.csv', 'NOVELTY_MATRIX.md', 'REJECTED_DESIGNS.md', 'configs/CANDIDATE_SPEC.lock.json', 'reports/B_RESOURCE.json', 'reports/CPU_EVALUATION_SUMMARY.json', 'reports/B_WHOLE_EVALUATION_SUMMARY.json', 'reports/B_SPARSE_SUMMARY.json'])
    historical('v8', V9 / 'rate_state_v5_pipeline_v8/results', ['FINAL_REPORT.ko.md', 'STATISTICAL_REVIEW.ko.md', 'SOURCE_GATE_REVIEW.ko.md'])
    historical('v9_R2', V9 / 'rate_state_v9/r2_evaluation/results', ['FINAL_REPORT.ko.md', 'EVALUATION_REPORT.ko.md', 'CPU_ABCD.csv', 'PAIRED_SUMMARY.csv', 'CLEAN_RESULTS.csv', 'EXECUTION_FAILURES.csv', 'COUNTERS_THROUGHPUT.csv', 'FINAL_EVIDENCE_AUDIT.json'])
    historical('v9_novelty', V9 / 'rate_state_v9/rate_track', ['NOVELTY_COLLISION.ko.md'])
    historical('v10_lifetime', V10 / 'native_lifetime_next', ['reports/FINAL_REPORT.ko.md', 'reports/FINAL_GATES.json', 'analysis/final/CPU_ABCD.csv', 'analysis/final/DIRECT_CONTRAST_SUMMARY.csv'])
    historical('v17_normal_pipeline', V15 / 'runtime/termination-v17-worktree/termination_v17/reports', ['FINAL_REPORT.ko.md', 'FINAL_ANALYSIS.json', 'FINAL_BINDINGS.json'])
    add('history/INDEX.json', js(history))

    normal = json.loads(payload['evidence/B4_reports/NORMAL_COST_CONTROLS.json'])
    add('data/NORMAL_COST_CONTROLS.csv', csv_bytes(normal['rows']))
    overall = {'status': 'ANALYSIS_SNAPSHOT_PARTIAL_NOT_TERMINAL_RESEARCH_CLOSURE', 'capture_started_UTC': started, 'closed_set_captured_UTC': captured, 'resource_observation_UTC': now(), 'resource_observation': resource, 'closed_new_round_records': len(closed), 'new_round_start_markers_captured': len(marker_paths), 'active_at_closed_capture': len(active), 'counts': [{'phase': p, 'status': s, 'count': n} for (p, s), n in sorted(counts.items())], 'B4_cohorts': {c: {k: x[k] for k in ('attempted_faults', 'valid_faults', 'failure_count', 'planned_fault_runs', 'phase_complete')} for c, x in analyses.items()}, 'B4_normal_records': {c: len(analyses[c]['clean']) for c in analyses}, 'preserved_failures_in_new_round': len(failures), 'raw_hash_checks': raw_verified, 'full_plan_global_CPU_needed': 4199, 'approved_global_CPU_cap': resource['CPU_cap'], 'extra_CPU_not_approved': max(0, 4199 - resource['CPU_cap']), 'no_new_CPU_or_rebuild_for_this_snapshot': True, 'source_worktree': str(W), 'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=W, text=True).strip(), 'HEAD_at_capture': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=W, text=True).strip(), 'scope': 'C++ and gem5; no new RTL/Cadence/SPICE/TCAD', 'exclusions': ['Active-run outputs and results created after the capture', 'ELF/build dependencies not needed for analysis', 'Full proprietary benchmark distributions, PDK, libraries, license data', 'All historical raw logs; selected historical summaries are included with hashes', 'Unrun EVAL data or imputed failed/missing cycles']}
    add('SNAPSHOT_STATUS.json', js(overall))
    add('README_FIRST.ko.md', readme(overall))
    add('RESULTS_AND_ANALYSIS.ko.md', report(overall, analyses, normal, failures))
    add('CHATGPT_PROMPT.ko.md', chatgpt_prompt())
    add('DATA_DICTIONARY.ko.md', dictionary())
    add('NEXT_AND_LIMITATIONS.ko.md', next_steps(overall))
    add('provenance/ORIGINAL_FILES.json', js(files))
    add('provenance/BUILD_COMMAND.json', js({'command': [sys.executable, '-B', str(pathlib.Path(__file__).resolve()), '--tag', args.tag], 'cwd': str(W), 'note': 'Read-only frozen-record analysis and packaging; no simulation dispatch.'}))
    index = {name: {'sha256': digest(data), 'bytes': len(data)} for name, data in sorted(payload.items())}
    add('SHA256_MANIFEST.json', js({'algorithm': 'sha256', 'self_excluded': 'SHA256_MANIFEST.json', 'files': index}))
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, data in sorted(payload.items()):
            z.writestr(name, data)
    zipdata = memory.getvalue()
    # Actual compressed bytes plus report copies, under the existing live budget.
    readable = ('README_FIRST.ko.md', 'RESULTS_AND_ANALYSIS.ko.md', 'CHATGPT_PROMPT.ko.md', 'NEXT_AND_LIMITATIONS.ko.md', 'SNAPSHOT_STATUS.json')
    r.snapshot(extra_MiB=(len(zipdata) + sum(len(payload[n]) for n in readable) + 1048576) / 1048576)
    out.mkdir(parents=True)
    artifact = out / ('BP_SEU_Results_ChatGPT_' + args.tag + '.zip')
    with artifact.open('xb') as f:
        f.write(zipdata)
    for name in readable:
        (out / name).write_bytes(payload[name])
    with zipfile.ZipFile(artifact) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist())) == len(payload)
        manifest = json.loads(z.read('SHA256_MANIFEST.json'))
        assert set(manifest['files']) | {'SHA256_MANIFEST.json'} == set(z.namelist())
        for name, ref in manifest['files'].items():
            data = z.read(name)
            assert len(data) == ref['bytes'] and digest(data) == ref['sha256']
    verification = {'status': 'PASS_ZIP_CRC_ALL_MEMBERS_SHA256_AND_CLOSED_RAW_HASHES', 'at_UTC': now(), 'artifact': str(artifact), 'sha256': digest(zipdata), 'bytes': len(zipdata), 'members': len(payload), 'raw_hash_checks': raw_verified, 'snapshot': overall, 'resource_after_package': r.snapshot()}
    (out / 'PACKAGE_VERIFICATION.json').write_bytes(js(verification))
    print(json.dumps({k: verification[k] for k in ('status', 'artifact', 'sha256', 'bytes', 'members', 'raw_hash_checks')}, indent=2))


def readme(s):
    dev, ev = s['B4_cohorts']['DEV'], s['B4_cohorts']['EVAL']
    return f'''# ELE548 TAGE SEU 연구 — ChatGPT 결과 분석 인계

이 ZIP은 **{s['closed_set_captured_UTC']}까지 닫힌 실제 실행**을 고정한 분석용 snapshot이다. 최종 캠페인 완료본이 아니다. 진행 중 실행은 중단/변경하지 않았고, 그 출력은 포함하지 않았다. 이후 완료된 결과와 이 snapshot의 수치를 섞지 않는다.

읽는 순서:
1. `RESULTS_AND_ANALYSIS.ko.md`: 연구 전체 경과, 프로그램별 정상/오류 결과와 한계.
2. `data/`: 최신 B4의 owner별 A/B/C/D, counter와 관측된 summary CSV/JSON.
3. `NEXT_AND_LIMITATIONS.ko.md`: 남은 실험과 해석 주의점.
4. `CHATGPT_PROMPT.ko.md`: 이 파일 내용을 ChatGPT에 붙여 넣고 ZIP을 첨부하면 된다.
5. `history/`: 과거 producer의 보존 결과. 최신 B4와 합산하거나 새 실험으로 인용하지 않는다.

최신 B4: C++ gate와 실제 O3 gate18 PASS. 정상 DEV {s['B4_normal_records']['DEV']}/18, 오류 DEV {dev['valid_faults']}/{dev['planned_fault_runs']} PASS·실패{dev['failure_count']}, 독립 EVAL 오류 {ev['valid_faults']}/{ev['planned_fault_runs']} PASS·실패{ev['failure_count']}. 종료 record가 없는 {s['active_at_closed_capture']}건은 진행 중/미완료로 제외했다. 모든 표는 이 고정 집합 기준이다.

전체 new round의 과거 실행 실패{s['preserved_failures_in_new_round']}건도 원본과 함께 보존한다. 최신 gate 성공으로 과거 실패를 성공으로 교체하지 않는다. 승인 CPU 상한{s['approved_global_CPU_cap']}, full corrected plan은4199회가 필요하다. +{s['extra_CPU_not_approved']}회는 현재 미승인이다.

이 자료는 C++/gem5 소프트웨어 모델 결과다. CPU 프로그램은 MiBench 유래 qsort/dijkstra/SHA이며 공식 SPEC 점수가 아니다. 정상 stage-fit/ports는 명시된 가정이다. RTL/PPA/방사선 실측 성능/mission FIT/full CPU 안전성의 증거가 아니다. 과거 독립 실험과 현재 개발 재검증을 구분한다.

무결성: `SHA256_MANIFEST.json`은 자기 자신을 제외한 모든 ZIP member의 SHA256/크기를 담는다. `raw_closed/`의 stats/config/event/종료 출력은 EXECUTION에 기록된 SHA와 실제 대조했다. `provenance/ORIGINAL_FILES.json`은 원래 경로와 ZIP 경로의 매핑이다. ELF/PDK/전체 build closure는 넣지 않았다. 원래 호스트 없이 **결과 분석**이 가능하도록 표와 모델 설명은 자족적으로 포함했다.
'''.encode()


def report(s, a, normal, failures):
    dev, ev = a['DEV'], a['EVAL']
    lines = [f'# 지금까지의 결과와 분석 경계\n\n고정 시각: {s["closed_set_captured_UTC"]}. 실험은 계속 진행 중이며 이 문서는 완료된 record만 반영한다.\n',
'''## 연구 질문과 비교 대상

장기 성능 피해를 만드는 TAGE 상태의 역할과 회복 차이를 확인하고, 정상 유지 비용과 오류 후 recovery 비용의 합을 줄이는 것이 목표다. 프로그램 정답은 완화하지 않는다. 고정 S*=346bits는 raw history130 + path16 + stored folded history200이다. P0·P_ED(parity+exclude/relearn)·SECDED·TMR가 필수 기준선이다. Periodic N1-style k64와 exact direct는 추가 비교군이다. Direct는 fold를 raw에서 정확히 계산하므로 없는 stored-fold S*346 공격과는 비교하지 않는다. SOURCE raw130와 WHOLE 추가 저장소 노출에서 비교한다.

이하 숫자는 **IMPLEMENTED/TESTED RESULT** 또는 실제 record로부터의 **NEW DERIVATION**이다. stage-fit/선택 rate/physical mapping은 **ASSUMPTION**이며 연구 가설은 결과와 별개다. 과거 논문 사실은 보존된 source review의 ID/PDF 페이지/절·표를 따른다.

## 연구 진행의 연결

|단계|실제 얻은 근거|남는 경계|
|---|---|---|
|E0/E1|gem5 pin과 logical-bit/no-fault/differential gate, Flying2129/2055/74 audit, S*346 선정|과제 trace와 CPU workload를 혼동하지 않음|
|기본 E2/E3 corrected RNG v2|동일 S* 세 보호법, CPU main4092·latency687 실제 측정. 지연0에서 피해 대부분 회복, 가정한 검사/복구 비용이 이득을 넘는 조건 관측|이상적 모델 결과를 최신 유한 pipeline 결과로 재사용하지 않음|
|cost-aware v3|N1/P의 낮은 정상 비용, P의 N1 대비 추가 이득은 대체로 작은 값·CI가0 포함|C++ 피해 감소가 CPU 우위나 novelty를 자동 보장하지 않음|
|pipeline v6–v8|queue/epoch/source-head/FIFO/metadata 실패를 보존하고 별도 수정·gate, 단일 pending 문제 확인|과거 v6 integrity PASS는 hardware safety PASS가 아님|
|v9 R2 독립162|새 입력에서 K2 parity escape·ECC DUE 비용·Direct/TMR 효과 비교, WHOLE 추가 state 포함|L0/C0 stage-fit 가정, owner2 탐색, 전체적인 Direct 승자 없음|
|v10/v11 R1/R8|장기 반복 유지에서 Direct 피해 감소, ECC/TMR과 같은 cycles 또는 parity가 빠른 조건, overwrite replication|유한 source/journal/RMW 비용을 완전히 포함하지 않음|
|v12–v17|실제 source/provider/finite queue와 sampling/visibility, 독립 요청 II1와 실제 CPU next-PC 의존성을 분리, early unconditional 중첩 성능 측정|직렬·native·direct의 자원 차이를 고정해야 공정한 보호 비교 가능|
|v18 B4 현재|동일 finite pipeline에 필수 보호법과 Direct, RMW encoding·retirement credit 오류를 새 producer에서 수정/재검증|개발/독립 matrix 아직 미완료, native 정상 비용이 큼|

과거 숫자의 상세 증거는 `history/INDEX.json`을 통해 확인한다. v3/v9/v17의 실행·owner·입력·timing 계약은 다르므로 다른 round의 A/B/C/D를 직접 조합하지 않는다. RNG namespace v1 superseded 결과는 이 인계의 최종 통계에 사용하지 않았다.

## 최신 B4 완료 범위
''']
    for cohort in ('DEV', 'EVAL'):
        x = a[cohort]
        lines.append(f'- {cohort}: 정상 {len(x["clean"])}/18, 오류 {x["attempted_faults"]}/{x["planned_fault_runs"]} closed; PASS{x["valid_faults"]}, FAIL{x["failure_count"]}.\n')
    lines += [f'- 고정 집합 밖 active/missing record: {s["active_at_closed_capture"]}건. old new-round 실패{len(failures)}건 보존. EVAL이0이면 미실행이며 CI나 우위를 만들지 않는다.\n',
'''- C++8gate, source-phase 346×5×5=8650, finite-retirement64/backpressure105cycles/metadata112SBU와 추가 admission edge gate가 통과했다.
- O3 checksum6 + overlap micro6 + mid-stage DUE6 =18 PASS. 전체 source/config/ELF hash와 원래 v17 ELF가 보존됨을 이 snapshot에서도 실제 검사했다.
- 이 gate는 테스트한 오류·상태 범위의 증거다. 모든 payload/추가 bit 정정, full CPU metadata, 수십억 protection-epoch wrap 또는 임의 다중 bit 안전성은 증명하지 않는다.

## 프로그램별 정상 비용: 무엇을 회복해야 하나

정상 DEV의 여섯 방식은 모두 cycles/instructions가 같았다. 공통 finite P0에도 no-op check/encode slot과 source 경로가 있으므로 **C−A=0을 실제 ECC/TMR 하드웨어 비용0으로 읽지 않는다.**

|프로그램|Native 정상 cycles|B4 정상 cycles|B4 IPC|보존 B2 serial 대비 cycles 변화|Native 대비 cycles 변화|실제 consume/source-cycle|max lookup pending|
|---|---:|---:|---:|---:|---:|---:|---:|
''']
    for row in normal['rows']:
        if row['method'] == 'P0':
            lines.append(f'|{row["program"]}|{row["native_clean_cycles"]:,}|{row["B4_pipeline_L1_cycles"]:,}|{row["B4_IPC"]:.6f}|{row["pipeline_vs_B2_serial_cycles_pct"]:+.4f}%|{row["pipeline_vs_native_clean_cycles_pct"]:+.4f}%|{row["actual_consumed_per_source_cycle"]:.6f}|{row["max_lookup_pending"]}|\n')
    lines += ['''
**관측의 의미:** qsort에서 중첩 효과가 가장 크지만 native 대비 정상 비용도 가장 크다. Dijkstra는 중간, SHA는 중첩 개선이 작다. 이 계약 내 실제 CPU outstanding 최대4는 독립 요청의 II1 가능성과 구별된다. 평균 consume≈0.118–0.141/source-cycle이므로 실제 dependent stream이 매 cycle 완료하는 것은 아니다.

**분리한 효과와 미확정 효과:** 같은L serial/early 대조는 client single-pending 제한과 known unconditional next-PC 중첩 효과를 포함한다. 이것을 모든 branch의 lookup latency 제거로 해석하지 않는다. Conditional next-PC/history/source ordering 대기는 남는다. SOURCE L2 대조는 source history/fold stage를 추가했고 provider/table LUT는1cycle로 고정되어 있다. 따라서 LUT 읽기 latency 자체만의 효과는 완전히 분리하지 못했다. 서로 겹치는 stall attempt 합은 CPI의 정확한 인과 분해가 아니다. 보존 B2 serial/L2는 옛 producer 대조이며 새 B4 반복 측정이 아니다. B4의 fresh normal과 기존 정상 cycles 일치는 별도로 확인했다.

## 오류 주입 A/B/C/D: 프로그램·노출별 완료된 값

A=동일 finite P0 정상, B=동일 owner 오류 P0, C=후보 정상, D=동일 owner 오류 후보 cycles다. 순이득 B−D >0이면 해당 조건에서 오류 P0보다 빠르다. `net %A=100(B−D)/A`. 정상 overhead=C−A. `D−C`에는 잔여 prediction 피해와 reset/relearning/queue 비용이 함께 있다. 순수 복구 시간의 단독 계측치가 아니다. Native matched-fault B는 이번 matrix에 없으므로 native 대비 절대 보호 순이득은 측정하지 못했다.

아래는 capture에 들어온 유효한 owner pair만 사용한다. DEV n=2는 개발용 탐색 통계이며 독립 평가/통계적 우위 증명이 아니다. n=1의 퇴화 CI는 표시하지 않는다. 음수·0·helpful 결과를 그대로 보존했다.

|cohort|프로그램|scenario|방법|valid/planned owners|mean B−D cycles|mean net %A|owner bootstrap95 cycles (탐색)|
|---|---|---|---|---:|---:|---:|---|
''']
    for cohort in ('DEV', 'EVAL'):
        for row in a[cohort]['paired_summaries']:
            ci = row['bootstrap95_cycles']
            lines.append(f'|{cohort}|{row["program"]}|{row["scenario"]}|{row["method"]}|{row["valid_pairs"]}/{row["planned_owners"]}|{row["mean_B_minus_D"] if row["mean_B_minus_D"] is not None else "NA"}|{format(row["mean_net_pct_A"], "+.6f") if row["mean_net_pct_A"] is not None else "NA"}|{ci if ci is not None else "NA"}|\n')
    if not dev['paired_rows'] and not ev['paired_rows']:
        lines.append('\n아직 유효한 오류 pair가 없다. 미실행 값을0으로 채우지 않았다.\n')
    lines += ['''
동일 A/C와 같은 owner의 여러 replay를 독립 표본으로 세지 않는다. Partial snapshot은 완료 순서에 따라 보이는 구성도 달라지므로 미완료 프로그램과 합친 pooled 승자를 선정하지 않는다. `data/*ABCD.csv`는 모든 owner별 A/B/C/D와 applied event/종료 censoring을 담고, `B4_ALL_CLOSED_COUNTERS.csv`는 실제 검출/정정/DUE/reset/refill와 wait를 담는다.

## 결함과 producer 교체: 실패를 숨기지 않는 이유

|producer|실제 발견/실패|새 producer 수정과 한계|
|---|---|---|
|A2|checksum2 FIFO occupancy/valid mismatch|B1은 source transaction의 실제 header로 repair하고 public accessor 재진입 제거|
|B1|SOURCE single-SBU parity2 timeout|B2는0-length Undo의 path restore도 accepted/committed version을 발행|
|B2|C++에서 RMW write 후 encode sample 전 source SEU가 손상값을 valid code로 재인코딩하는 반례|B3는 dispatch에서 실제 post-image를 등록해 encoder로 전달. B2 보호 qualification 철회; 정상 old controls는 별도 보존|
|B3|SOURCE qsort ECC2bit DUE/reset 후 committed history without finite ingress credit|B4는 actual retirement의 credit check/enqueue를 함께 수행하고 지연 training의 재등록 제거, cycle당 committed ingress1회|
|B4|현재 gate와 완료된 프로그램 범위에서 새 실패 여부는 실제 count/CSV 참조|전체 DEV/EVAL 미완료이므로 pending gate 성공을 모든 반복 오류 안전성으로 확대하지 않음|

B3 O3 실패 당시 queue count/prepared 값은 저장되지 않았다. C++ delayed8/다섯번째 ingress4 overflow는 같은 경로의 한 구체적 반례이며 실제 O3의 내부 개수를 측정한 것은 아니다. B4 prepared squash/pre-reset training edge도 별도 검증했다. CPU가 실행 중인 binary/source를 수정하지 않았으며 모든 교체는 별도 producer/build/output에서 수행했다.

## Fault model: 출처와 가정

- **SOURCE FACT:** CHARM L06 원문 PDFp13 TableII 첫6T 관측205 SBU/9 MCU2를 K mark 분포로 사용했다. 같은 페이지 TableIII는 K3/K≥4도 있어 K≤2가 자연법칙이라는 주장은 할 수 없다. 논문/파일의 측정 대상과 이 predictor/공정은 다르다.
- **ASSUMPTION:** SOURCE raw130은 Poisson rate2000 events/s, 2GHz에서 λ=1e−6event/cycle, K1=205/214·K2=9/214. Logical age의 연속Kbit를 한 사건으로 atomic XOR한다. 임의 physical 인접성/28nm 측정 rate가 아니다. 사건 rate를 E[K]로 나눠 bit rate와 바꾸지 않는다.
- **ASSUMPTION:** WHOLE은 역사적 reference `(1.05e−14×20/3600) per-bit/s`에 stress scale1e15를 곱하고 실제 method/union manifest로 thinning한다. 새 storage가 늘면 노출도 늘며 latent union population은79429다. 면적 비율을 cross section으로 사용하지 않는다. 임무 FIT/선량 등가가 아니다.
- SSTAR346_SINGLE_SBU는 cleanP0 시간창에 한 번, 균일 logical site/time을 고른 조건부 공격이다. 시간 rate 추정 실험이 아니다. Direct는 folded state가 없어 이 비교 N/A다.
- Master DEV30b / EVAL31b 계열, input32b 계열, time/K/location namespace-v2 PCG64를 분리한다. Predictor RNG는 별개다. 정확한 entropy와 owner는 preregistry에 기록되어 있다. 500ticks/cycle, 4H tape와 최초 정상 program exit censoring을 유지한다. 보호법별 종료 시간이 달라 실제 적용 사건 수가 달라도 latent tape를 재추첨하지 않는다.
- Flying Laptop은2129raw/2055distinct/74duplicate-extra다. 중복을 MCU로 세지 않는다. CERN clock-labelled xadd/coordinate cluster를 독립 particle나 target physical MCU/rate로 바꾸지 않는다. 원문 분류·threshold 접근 한계는 보존 source review에 있다. 이번 B4 SOURCE/WHOLE 표는 CERN 물리 교정 실험이 아니다.

## Logical storage와 안전 경계

Actual L1 manifest: P0 77627 / frequent·periodic parity 77673 / ECC77869 / TMR79011 / Exact Direct76611bits. P0 대비 parity+46, ECC+242, TMR+1384, Direct−1016은 선언한 logical storage의 산술이다. RTL 최적화 면적·지연·에너지나 방사선 단면적은 아니다. Latch/queue/ID/epoch/control과 새 commit-used bit는 WHOLE에 포함했다.

S*밖 retention1000bit가 undo 때 재진입할 수 있고 독립 coding witness는 없다. Uncoded encoder operand latch 오류는 ECC code나 두 TMR replica를 함께 오염시킬 수 있다. even-parity/SECDED3+/correlated TMR은 보장 밖이다. CPU-owned BranchInfo/expected token/BTB/RAS/architectural state, 기존 allocator/aging/RNG 및 일부 absolute software clock은 manifest의 명시적 제외 범위다. `corrected` counter는 decoder/vote 동작이며 golden 전체 상태 복구의 증거가 아니다. Program 정답/종료 성공도 영구 무해/전체 상태 동일성을 보장하지 않는다.

## 지금 지지되는 결론과 다음 분석 질문

1. 손상된 history/fold 관계의 장기 피해를 줄이는 구조적 아이디어는 유효한 연구 대상으로 남는다. Direct folding 자체는 BADGR 등 선행연구와 겹치므로 신규 발명으로 주장하지 않는다.
2. 유한 pipeline의 실제 중첩은 직렬 대비 일부 정상 대기를 줄였다. 그러나 native 정상 대비 큰 비용, next-PC/history/ordering 의존성은 남았고 이 둘을 감안하지 않은 protection 승자는 없다.
3. 최신 B4의 프로그램·owner별 이득은 위 완료 범위만의 결과다. 과거 v3 P/N1·v9 Direct/K2·v10 R8 결과는 다른 resource 계약의 근거로 보존한다. 수치를 합쳐 새 승자를 만들지 않는다.
4. 신규성의 가능한 범위는 사건 구조/역할별 오류 수명/복구 정책과 정상+recovery 비용의 조건부 설계 지침이다. 최종 우위/최소 비용 구조/전체 하드웨어 안전성은 미확정이다.

추가 실험의 우선순위와 미승인 예산은 `NEXT_AND_LIMITATIONS.ko.md`를 따른다. 이 snapshot을 만드는 과정에서 CPU 실행0, rebuild0, 실행 중 job 변경0이다.
''']
    return ''.join(lines).encode()


def chatgpt_prompt():
    return '''첨부 ZIP은 ELE548 TAGE SEU 연구의 실제 결과 분석용 snapshot이다. 먼저 README_FIRST.ko.md, RESULTS_AND_ANALYSIS.ko.md, SNAPSHOT_STATUS.json을 읽고 data/의 owner별 A/B/C/D 및 counter로 수치를 확인해줘. history/는 다른 producer/resource/입력의 과거 결과이며 현재 B4 결과로 섞지 말아줘. 현재 snapshot 이후 종료한 실행은 여기 없고, 진행 중·미실행·실패를0 또는 masked fault로 만들지 말아줘.

우리 연구 질문은 “SEU가 만든 장기 성능 피해를 끊으면서 정상 보호 비용+오류 이후 recovery 비용을 최소화하는 TAGE 상태 보호/회복 구조가 무엇인가?”이다. 프로그램 정답은 완화하지 않는다. 고정 S*=346 raw130/path16/fold200에 P0/P_ED(검출+exclude/relearn)/SECDED/TMR는 필수 기준선이고 periodic N1-style·Exact Direct는 추가 후보다. Direct의 absent stored-fold에 대한 SSTAR346 공격은 N/A다. SOURCE raw130 조건부 공격과 전체 추가 state 포함 WHOLE 노출을 구분한다.

분석해줄 내용:
1) 프로그램별로 정상 costs, 오류 피해, B−D 순이득, owner 변동/CI/실패/미완료 범위를 설명해줘. Native 정상과 finite P0 기준을 구분하고 native-fault B가 없다는 한계를 명시해줘.
2) 파이프라인으로 실제 줄어든 대기와 남은 next-PC/history/source ordering 의존성을 구분해줘. Independent II1를 실제 branch stream1/cycle로 해석하거나 stall 합을 CPI의 정확한 인과 분해로 사용하지 말아줘.
3) P_ED/ECC/TMR과 Exact Direct/N1-style의 비용-회복 tradeoff에서 현재 지지되는 결론과 미확정 사항을 분리해줘. C−A=0은 공통 stage-fit 모델 결과이며 실제 보호 회로 비용0이 아니야.
4) B2 RMW encoding 결함과 B3 retirement ingress 실패가 기존 결론의 범위를 어떻게 제한하는지 검토해줘. 수정된 B4 gate 성공을 전체 safety/독립 성능 우위로 확대하지 말아줘.
5) 보존 선행연구 충돌표를 참고해 novelty 주장을 좁혀줘. SOURCE FACT/NEW DERIVATION/DESIGN HYPOTHESIS/IMPLEMENTED RESULT/ASSUMPTION을 구분하고 출처 없는 논문/수치를 만들지 말아줘.
6) Cadence 없이 다음에 할 C++/gem5 실험을 적은 수의 우선순위로 제안해줘. 먼저 현 cohort를 끝내고 입력·seed·자원 조건을 고정한 평가와, 추가 native-fault 대조/원인 분리의 필요성을 비교해줘. 추가 예산 제안은 실제 사용자 승인과 구분해줘.

DEV owner2는 탐색용이다. EVAL owner8도 workload 모집단 전체를 대표하지 않는다. 같은 tape의 여섯 replay나 공유 A/C를 독립 표본으로 세지 말아줘. Helpful/zero fault와 적용 사건의 first-exit censoring을 유지해줘. TCAD는 사용할 수 없고 이번 범위는 C++/gem5까지야. 새 RTL/Cadence/SPICE/TCAD나 mission FIT/실측 chip 성능을 주장하지 말아줘.
'''.encode()


def dictionary():
    return '''# 데이터 사전

- `SNAPSHOT_STATUS.json`: 시작 marker와 닫힌 record 집합의 고정 시각, 별도 resource 관측 시각, 승인 예산, active 제외 수. 실행 중 새 record 생성 때문에 resource 관측의 active 수와 고정 집합의 active 수는 달라질 수 있다.
- `data/B4_DEV_ABCD.csv`, `B4_EVAL_ABCD.csv`: 행 단위 program/scenario/method/owner. A=finite P0 clean; B=동일 owner P0 fault; C=method clean; D=method fault. valid_pair=false이면 B/D/net을 임의 대입하지 않는다. P0 행은 자기 대조이며 net0이 맞다. 대상 method record 자체가 아직 없으면 행도 아직 없다.
- net_cycles=B−D; net_pct_A=100(B−D)/A. clean_overhead=C−A. residual_damage=D−C는 prediction 피해+실제 recovery/queue/재학습 비용의 합이다.
- applied_events/future_censored는 method 자체의 최초 program-exit 경계다. 같은 latent owner라도 방법별 종료 시각·WHOLE thinning으로 event 수가 달라진다. NaN/빈 cell을0으로 채우지 않는다.
- `*_PAIRED_SUMMARY.csv`: cell마다 observed/valid/failed/planned owners를 구분한다. n1 CI를 생략했다. n2는20,000 owner bootstrap의 탐색 기술통계다. exact sign/Holm은 기존 분석 정의를 보존하되 partial cell/개발 자료의 사후 우위 선정에 사용하지 않는다.
- `*_CLEAN.csv`: 실제 cycles/IPC, accepted/produced/consumed per source-cycle와 max outstanding, normal check/encode. source_cycle과 CPU cycle의 구체적 관계는2GHz/500ticks 계약에 따른다.
- `B4_ALL_CLOSED_COUNTERS.csv`: program-exit frozen counters를 우선한다. protection_unit_busy는 API rejection 횟수이며 busy cycles가 아니다. unverified_retention_reentries는 Undo dispatch(0-length 포함) 수이며 손상 bit 수가 아니다. corrected는 code/vote 동작이고 golden 정답 복구 판정이 아니다. Stall/wait는 겹칠 수 있다.
- `raw_closed/<label>/EXECUTION.json`: 원래 status/producer/command/task/ref와 cycles/IPC/종료 counter/hash. 같은 폴더의 실제 raw 출력은 기록된 SHA와 대조했다. 주입 전후/events/detector trace와 stats/config/정답 출력이 함께 있다.
- `data/RETAINED_EXECUTION_FAILURES.csv`: A2/B1/B3 실패 원본. cycles null을 성능0이나 masked로 바꾸지 않는다. timeout/인계 진단 run은 정답 성공이 아니다. 이전 v6/v8/v9 실패는 history 보고서에 따로 있다.
- `plans/`: 이미 존재하는 frozen schedule plan. 미래 schedule은 설계 정보이지 실행 결과가 아니다. `schedules/`는 닫힌 CPU record가 참조한 실제 tape다.
- `provenance/`: ZIP member와 원래 경로/해시 연결, compiled producer·원래 v17 ELF 보존 검사. ELF/전체 build closure는 제외하여 ChatGPT용 분석에 집중했다.

CSV는 UTF-8 BOM이다. nested counter/maps는 JSON 문자열로 저장했다. 소수점 변환/보고 round-off 이외에 raw 숫자는 임의 수정하지 않았다. history의 절대경로 링크는 원호스트용이며 ZIP 안에서는 history/INDEX.json의 archive_path를 사용한다.
'''.encode()


def next_steps(s):
    return f'''# DONE / NOT DONE / ASSUMPTIONS / BLOCKERS / NEXT

DONE: {s['closed_set_captured_UTC']}까지 닫힌 실제 CPU record, 최신 C++/O3 gate, 프로그램별 normal controls와 owner별 A/B/C/D를 고정했다. 모든 포함 raw hash와 producer/기존 ELF를 검사했다. 과거 corrected RNG v2·v3·v8·v9R2·v10 lifetime·v17 정상 결과를 구분해 포함했다. snapshot 구성은 CPU/build 실행0이다.

NOT DONE: B4 전체 DEV102/독립 EVAL408과 최종 고정 후보 평가가 완료된 것은 아니다. 정확한 상태는 SNAPSHOT_STATUS.json이다. Native matched-fault B, finite-controller 비용의 완전한 인과 분해, source/latch/control 모든 오류의 안전성, 장기 종료 이후 tail, RTL/PPA·실제 energy/mission rate는 미측정이다.

VERIFIED ASSUMPTIONS: source/protection23-lane stage-fit, finite queue/ports/II 규약,2GHz/500ticks, stress rate 및 physical mapping 제외를 문서화했다. Decoder를 golden/injector와 분리하고 event RNG/predictor RNG를 분리했다. 이 모델에서 실행했다고 물리 달성성이 검증된 것은 아니다.

BLOCKERS: 현재 승인 CPU cap={s['approved_global_CPU_cap']}이며 full corrected plan은4199회를 요구한다. +{s['extra_CPU_not_approved']}회는 현재 실제 승인 파일이 없으면 미승인이다. 이미 실행 중인 worker는 기존 상한에서 계속할 수 있으며 이 ZIP 요청으로 중단하지 않았다. 이전 상한108coreh 문서는 현 round160·합산 global252coreh 실제 승인으로 갱신된 계약과 구분한다. 예산 부족은 환경/license 실패가 아니다.

NEXT, 현재 승인 범위:
1. 기존 frozen coordinator/producer를 유지하고 남은 DEV를 완료한다. 실패면 해당 단계 fail-closed하고 원본·명령을 보존한다. 새 source 수정은 별도 producer와 gate를 요구한다.
2. 이미 고정된 후보/resource/새 입력/독립 owner로 EVAL clean18+fault408을 수행한다. 개발 재시도를 independent holdout이라고 부르지 않는다. 기존 CPU cap이 먼저 닿으면 필요한 미실행 case·다음 명령을 남기고 임의 초과하지 않는다.
3. 충분히 완료된 뒤 프로그램/scenario별 matched-owner B−D와 정상 비용·recovery·통과/실패를 보고한다. partial 순위로 후보를 바꾸거나 favourable seed로 재추첨하지 않는다.

DESIGN HYPOTHESIS / 새 승인 전 계획 제안:
4. 원래 native의 동일 owner SOURCE/WHOLE fault B 대조가 필요한지 판단한다. 현재 finite A에 대한 이득은 native 정상 overhead를 상쇄했다는 증거가 아니므로 이 대조는 절대 배포 이득 판단의 가장 직접적인 공백이다. manifest/physical-write 의미 차이까지 사전 고정해야 한다.
5. 같은 source/protection resource에서 lookup-only L/II/client-pending 제어를 더 좁혀 stage latency와 conditional next-PC/history 의존성을 분리한다. 이때 source L2만 바꾼 결과를 LUT read latency 결과로 부르지 않는다. RMW/journal pipeline 변경은 별도 변형이다.
6. 정상 source/commit ordering 비용이 큰 원인을 실제 causal counterfactual로 좁히고 retirement/history service 개선을 새 후보 최대1–2개로 검토한다. cost-only diagnostic은 실제 설계 결과가 아니다. 추가 metadata/retention/uncoded stage-latch 노출을 늘려 교환조건을 분석한다.

이후 새 실험 규모/시간/디스크는 현재 완료 시간 실측으로 정하고 예산에 맞춰야 한다. 이 ZIP은 새 무제한 campaign 권한이 아니다. 기존 S*346 P0/P_ED/ECC/TMR·native·Direct·과거 실패를 보존한다. 이번 후속은 C++/gem5로 한정하며 RTL/Cadence/SPICE/TCAD는 진행하지 않는다.
'''.encode()


if __name__ == '__main__':
    main()
