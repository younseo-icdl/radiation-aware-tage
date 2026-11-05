"""Independent owner arithmetic and small completed-results handoff; no CPU run."""
import collections
import csv
import datetime
import hashlib
import io
import json
import pathlib
import statistics
import sys
import zipfile

sys.dont_write_bytecode = True
ROOT = pathlib.Path(__file__).resolve().parents[2]
K = ROOT / 'runtime/continuation_b4'
sys.path.insert(0, str(ROOT / 'continuation_b4/tools'))
import resources as r


def js(x):
    return (json.dumps(x, ensure_ascii=False, indent=2) + '\n').encode()


def sha(x):
    return hashlib.sha256(x).hexdigest()


def csvdata(rows):
    out = io.StringIO(newline='')
    fields = list(dict.fromkeys(k for row in rows for k in row))
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: json.dumps(x, ensure_ascii=False) if isinstance(x, (list, dict)) else x for k, x in row.items()})
    return out.getvalue().encode('utf-8-sig')


def main():
    assert r.load(K / 'reports/RESUME_4199_COMPLETED.json')['status'].startswith('PASS')
    audit = r.load(K / 'reports/ACTUAL_TERMINAL_AUDIT_4199.json')
    assert audit['status'] == 'PASS_COMPLETED_B4_MATRIX_AUDIT_NOT_HARDWARE_QUALIFICATION'
    state = r.snapshot()
    assert state['CPU_global'] == state['CPU_cap'] == 4199 and state['active'] == 0
    analyses, verified, closed = {}, [], []
    for cohort, nfault, nowner in [('DEV', 102, 2), ('EVAL', 408, 8)]:
        clean, fault = [], []
        for kind, dest in [('CLEAN', clean), ('FAULT', fault)]:
            tasks = r.load(K / 'runtime/configs' / (cohort + '_' + kind + '_FULL.lock.json'))['tasks']
            assert len(tasks) == (18 if kind == 'CLEAN' else nfault)
            for task in tasks:
                path = pathlib.Path(task['output']) / 'EXECUTION.json'
                row = r.load(path)
                assert row['task'] == task and row['status'].startswith('PASS')
                dest.append(row)
                closed.append(row)
        A = {x['program']: x['cycles'] for x in clean if x['method'] == 'P0'}
        C = {(x['program'], x['method']): x['cycles'] for x in clean}
        B = {(x['program'], x['task']['scenario'], x['task']['owner']): x['cycles'] for x in fault if x['method'] == 'P0'}
        D = {(x['program'], x['task']['scenario'], x['method'], x['task']['owner']): x['cycles'] for x in fault}
        analysis = r.load(K / 'reports' / (cohort + '_ANALYSIS.json'))
        assert analysis['attempted_faults'] == analysis['valid_faults'] == nfault and analysis['failure_count'] == 0
        assert len(analysis['paired_rows']) == nfault
        for row in analysis['paired_rows']:
            program, scenario, method, owner = (row[k] for k in ('program', 'scenario', 'method', 'owner'))
            values = [A[program], B[program, scenario, owner], C[program, method], D[program, scenario, method, owner]]
            assert row['valid_pair'] and values == [row[k] for k in 'ABCD']
            assert row['net_cycles'] == values[1] - values[3]
            assert row['clean_overhead'] == values[2] - values[0]
            assert row['residual_damage'] == values[3] - values[2]
            assert abs(row['net_pct_A'] - 100 * row['net_cycles'] / values[0]) < 1e-12
            verified.append((cohort, program, scenario, method, owner))
        for group in analysis['paired_summaries']:
            rows = [x for x in analysis['paired_rows'] if all(x[k] == group[k] for k in ('program', 'scenario', 'method'))]
            assert len(rows) == group['observed_owners'] == group['valid_pairs'] == nowner
            assert group['failed_pairs'] == 0
            assert statistics.mean(x['net_cycles'] for x in rows) == group['mean_B_minus_D']
            assert abs(statistics.mean(x['net_pct_A'] for x in rows) - group['mean_net_pct_A']) < 1e-12
        analyses[cohort] = analysis
    assert len(set(verified)) == len(verified) == 510
    normal_native = r.load(ROOT / 'reports/NATIVE_REFERENCE6.json')
    native = {(x['label'].split('.')[1], x['task']['program']): x['cycles'] for x in normal_native['rows']}
    payload = {}
    for cohort, analysis in analyses.items():
        payload['data/' + cohort + '_ABCD.csv'] = csvdata(analysis['paired_rows'])
        payload['data/' + cohort + '_PAIRED_SUMMARY.csv'] = csvdata(analysis['paired_summaries'])
        payload['data/' + cohort + '_CLEAN.csv'] = csvdata(analysis['clean'])
        payload['data/' + cohort + '_ANALYSIS.json'] = js(analysis)
    payload['data/B4_ALL546_CLOSED_RECORDS.json'] = js(closed)
    counters = []
    for row in closed:
        counters.append({**{k: row.get(k) for k in ('label', 'phase', 'program', 'method', 'cycles', 'IPC', 'applied_events', 'applied_flips', 'host_cpu_seconds', 'wall_seconds')}, 'owner': row['task'].get('owner'), 'scenario': row['task'].get('scenario'), **row['program_exit_seu']})
    payload['data/COUNTERS.csv'] = csvdata(counters)
    check = {'status': 'PASS_INDEPENDENT_RECOMPUTATION_ALL510_OWNER_ROWS_AND102_SUMMARY_CELLS', 'at_UTC': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'DEV_fault_rows': 102, 'EVAL_fault_rows': 408, 'clean_rows': 36, 'all_B4_program_rows': 546, 'independence_unit': 'owner within program/scenario; shared A/C and method replays are not extra samples', 'implementation': r.ref(__file__), 'source_audit': r.ref(K / 'reports/ACTUAL_TERMINAL_AUDIT_4199.json'), 'no_new_CPU': True}
    payload['INDEPENDENT_ARITHMETIC_AUDIT.json'] = js(check)
    for path in [ROOT / 'reports/CPU_4199_AUTHORIZATION.lock.json', ROOT / 'reports/PRODUCER_B4.lock.json', ROOT / 'reports/B4_CORRECTNESS_ACCEPTANCE.json', ROOT / 'sources/B4_SOURCE_AND_LOGICAL_MANIFEST.lock.json', ROOT / 'sources/B4_FAULT_AND_RESOURCE_MODEL_CARD.ko.md', ROOT / 'docs/02_IMPLEMENTED_RESOURCE_CONTRACT.ko.md', K / 'reports/ACTUAL_TERMINAL_AUDIT_4199.json', K / 'reports/ACTUAL_TERMINAL_REPORT_4199.ko.md', K / 'reports/RESUME_4199_COMPLETED.json', K / 'reports/RESUME_4199_PRECHECK.json', K / 'reports/FINALIZER_4199_DERIVATION.json', K / 'reports/NATIVE_BREAK_EVEN_THRESHOLDS.json', K / 'reports/COHORT_PREREGISTRATION.lock.json', K / 'reports/COHORT_INPUTS.lock.json', K / 'reports/CANDIDATE_EVALUATION_FROZEN.lock.json', K / 'reports/NORMAL_COST_CONTROLS.json', K / 'reports/NATIVE_B4_EVAL_SYSTEM_CONFIG_GATE.json', K / 'reports/software.lock.json']:
        payload['evidence/' + path.name] = path.read_bytes()
    payload['tools/report_completed.py'] = pathlib.Path(__file__).read_bytes()
    payload['tools/resume_eval.py'] = pathlib.Path(__file__).with_name('resume_eval.py').read_bytes()
    payload['evidence/software_completed_4199.lock.json'] = (K / 'reports/software_completed_4199.lock.json').read_bytes()
    report = ['# B4 유한 자원 보호 비교 — 승인4199회 완료', '', 'DONE: 기존370건을 보존하고 같은 frozen plan의 미시작38건만 추가했다. DEV 정상18/오류102, 독립 EVAL 정상18/오류408 전부 프로그램 정답·유한 프로토콜 gate PASS다. B4 O3 gate18은 별도이며 과거 실패5/진단1은 원본 그대로 남는다. 새 구현/binary·입력·seed·사건 법칙·schedule 변경은 없다.', '', '기존 단일 pending 결과·v3/v9/v17 및10/18부분 handoff는 보존했다. 이 보고서는 완료된 B4의 추가 자료이며 이전 snapshot 수치를 덮어쓰지 않는다.', '', '## 독립 평가 프로그램별 정상 비용', '', '|프로그램|Native EVAL 정상 cycles|B4 EVAL 정상 cycles(여섯 방법 공통)|IPC|Native 대비 정상 증가%|실제 consume/source-cycle|max lookup|', '|---|---:|---:|---:|---:|---:|---:|']
    for x in analyses['EVAL']['clean']:
        if x['method'] == 'P0':
            na = native['EVAL', x['program']]
            report.append(f"|{x['program']}|{na:,}|{x['cycles']:,}|{x['IPC']:.6f}|{100*(x['cycles']/na-1):+.4f}|{x['consumed_per_source_cycle']:.6f}|{x['max_lookup_pending']}|")
    report += ['', 'ASSUMPTION: 공통 check/encode/provider stage-fit을 finite P0에도 적용했다. C−A=0은 실제 ECC/TMR 회로 비용0이 아니다. Native fault B는 미측정이며 아래 B−D는 같은 finite P0 대비 이득이다.', '', '## 독립 평가 순이득 B−D', '', 'A/B=정상/오류 finite P0, C/D=정상/오류 후보. net%=100(B−D)/A. 프로그램/scenario별 독립 owner8이며 paired bootstrap95%는 탐색적 추정이다. 음수/0/helpful를 보존하고 같은 tape의 replay나 공유 A/C를 추가 표본으로 세지 않는다.', '', '|프로그램|조건|방법|mean B−D cycles|net%A|paired95% cycles|positive/zero/negative|Holm sign p|', '|---|---|---|---:|---:|---|---|---:|']
    for x in analyses['EVAL']['paired_summaries']:
        if x['method'] == 'P0':
            continue
        ci = x['bootstrap95_cycles']
        report.append(f"|{x['program']}|{x['scenario']}|{x['method']}|{x['mean_B_minus_D']:,.3f}|{x['mean_net_pct_A']:+.6f}|[{ci[0]:,.1f}, {ci[1]:,.1f}]|{x['positive_owners']}/{x['zero_owners']}/{x['negative_owners']}|{x.get('Holm_sign_p_within_program_scenario')}|")
    report += ['', '프로그램/scenario별 차이와 full owner값은 CSV/JSON을 우선한다. 각 방법이 같은 P0보다 유리한지와 Direct가 다른 보호법보다 유리한지는 다른 비교다. 같은 P0 기준 CI들만 보고 후보 간 유의한 우위를 추론하지 않는다. Methods paired contrast가 필요하면 동一owner의 D를 직접 빼야 한다.', '', '## 비용·보호 범위·미확정', '', '- 고정 S*=raw130/path16/fold200=346bit에 P0/P_ED/SECDED/TMR를 유지했다. periodic N1-style k64와 Exact Direct는 추가 비교군이다. Direct는 없는 stored-fold에 대한 SSTAR346 공격 N/A이고 SOURCE/WHOLE에서 여섯 방법을 비교한다.', '- B−D=(B−A)−(C−A)−(D−C). D−C에는 잔여 prediction 피해와 reset/refill/queue/relearning 비용이 함께 포함된다. 겹치는 stall 횟수의 합은 정확한 CPI 인과분해가 아니다.', '- Native matched-fault B가 없으므로 NATIVE_BREAK_EVEN_THRESHOLDS는 실제 native A와 finite D로 계산한 손익분기 가설이다. native 보호 순이득을 측정한 결과가 아니다.', '- 독립 요청 II1와 실제 dependent branch stream throughput를 구분한다. early 중첩으로 줄어든 대기는 보존된 DEV serial 대조에서 확인했으며 conditional next-PC/history/source ordering 의존성은 남는다. SOURCE L2는 LUT 자체 read latency 단독 효과가 아니다.', '- SOURCE λ2000events/s/K1=205/214·K2=9/214와 WHOLE per-bit reference×1e15는 대상 칩 실측 rate가 아닌 명시적 stress이다. 역할별 RNGv2·500ticks/cycle·4H horizon·first-exit censoring을 바꾸지 않았다. Helpful/zero/future-censored 사건을 유지한다.', '- WHOLE에는 새 latch/queue/ID/epoch/control과 보호 storage를 포함하나 uncoded latch·retention 재진입 및 CPU-owned state 제외의 한계가 있다. Decoder corrected는 golden 전체 상태 복구가 아니다. 모든 predictor bit/full CPU safety를 보장하지 않는다.', '', '## 실행과 자원', '', f"실제 CPU global{state['CPU_global']}/{state['CPU_cap']}, new round 기록{state['round_recorded_coreh']:.6f}/160coreh, active0. 과거CPU를 차감하거나 재설정하지 않았다. 첫 묶음22병렬은 기존1GiB namespace cap 안에서 output 증가와 active 예약 공간을 함께 계산한 결과다. shared 최대32는 유지했다.", '', 'BLOCKERS: 승인된 primary matrix에 추가 사용자 행동은 없다. 전체 ELF/raw를 중복하는 큰 bundle은 기존 disk cap에서 자동 허용하지 않는다. 이 compact delta는 분석 표·보고서·해시 연결을 담고, full raw/ELF는 원래 경로에 보존했다.', '', 'NOT DONE: 실제 RTL/PPA/energy, measured chip/mission FIT, native matched-fault CPU, full CPU metadata safety, 장기 종료 이후 tail, LUT latency의 완전한 인과 분리.', '', 'NEXT: 프로그램별 recovery 이득과 정상 finite 비용을 함께 검토한다. Native-fault 대조, source/commit ordering 정상 비용의 좁은 인과 실험, 추가 latch/retention 노출이 후속 소프트웨어 가설이다. CPU 상한4199에 도달했으므로 새 CPU를 더 발행하지 않는다. RTL/Cadence/SPICE/TCAD는 진행하지 않았다.']
    text = '\n'.join(report).replace('동一owner', '동일 owner') + '\n'
    payload['COMPLETED_REPORT.ko.md'] = text.encode()
    payload['CHATGPT_PROMPT.ko.md'] = '이 ZIP은 이전10/18부분 snapshot의 후속 B4 완료 결과다. COMPLETED_REPORT.ko.md와 EVAL/DEV_ABCD 및 PAIRED_SUMMARY CSV/JSON으로 프로그램별 순이득·CI·실패·normal/recovery 비용을 분석해줘. B4 정상36/개발fault102/독립fault408 전부 통과했고 과거5실패/1진단은 보존했다. Native fault B는 없으므로 finite P0 대비 이득을 native 대비 승리로 바꾸지 말아줘. C−A=0은 공통 finite stage 가정이지 실제 회로 비용0이 아니야. 기존 기본 보호법 P0/P_ED/ECC/TMR, optional N1-style/Direct, SOURCE와WHOLE 및SSTAR의비교범위를구분해줘. Owner가표본단위이며candidate간유의차이는동일owner D대조를사용해줘. 새실험제안은가설로표시하고TCAD는불가·RTL/Cadence/SPICE는보류하며C++/gem5범위로정리해줘.\n'.encode()
    payload['SHA256_MANIFEST.json'] = js({name: {'sha256': sha(data), 'bytes': len(data)} for name, data in sorted(payload.items())})
    memory = io.BytesIO()
    with zipfile.ZipFile(memory, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for name, data in sorted(payload.items()):
            z.writestr(name, data)
    data = memory.getvalue()
    out = ROOT / 'handoff_analysis/20261019_completed_4199'
    assert not out.exists()
    r.snapshot(extra_MiB=(len(data) + len(payload['COMPLETED_REPORT.ko.md']) + 1048576) / 1048576)
    out.mkdir()
    path = out / 'BP_SEU_B4_Completed4199_Results_20261019.zip'
    with path.open('xb') as f:
        f.write(data)
    for name in ('COMPLETED_REPORT.ko.md', 'CHATGPT_PROMPT.ko.md', 'INDEPENDENT_ARITHMETIC_AUDIT.json'):
        (out / name).write_bytes(payload[name])
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist())) == len(payload)
        for name, ref in json.loads(z.read('SHA256_MANIFEST.json')).items():
            assert sha(z.read(name)) == ref['sha256'] and len(z.read(name)) == ref['bytes']
    r.put(out / 'PACKAGE_VERIFICATION.json', {'status': 'PASS_CRC_ALL_MEMBER_SHA_AND510_ABCD', 'zip': r.ref(path), 'bytes': len(data), 'members': len(payload), 'resources_after': r.snapshot()})
    print('REPORT_AND_COMPACT_RESULTS_CREATED', str(path), len(data), flush=True)


if __name__ == '__main__':
    main()
