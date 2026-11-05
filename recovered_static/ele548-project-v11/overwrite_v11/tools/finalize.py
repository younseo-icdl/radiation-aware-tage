#!/usr/bin/env python3
"""Close this bounded gate and prepare, but never dispatch, the next12 cases."""
from pathlib import Path
import csv, datetime, hashlib, io, json, shutil, subprocess, sys

BASE = Path(__file__).resolve().parents[1]
ROOT = BASE.parent
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
    # Reuse valid immutable partial analysis after a failed finalizer only if
    # the values match exactly. Never overwrite a record or successful gate.
    if (REPORT / name).exists():
        assert read(REPORT / name) == obj, ('EXISTING_ANALYSIS_DIFFERS', name)
        return
    with (REPORT / name).open('x') as f:
        json.dump(obj, f, indent=2); f.write('\n')

def kib(p):
    return int(subprocess.check_output(['du', '-sk', str(p)], text=True).split()[0])

def main():
    cpu_path = REPORT / 'CPU_REGRESSION.json'
    cpu = read(cpu_path)
    assert cpu['status'] == 'PASS_ALL6_OVERWRITE_ZERO_FAULT_CPU_REGRESSIONS_NOT_COST_VALIDATION'
    assert cpu['actual_global_cpu'] == 3475 and cpu['new_cpu_runs'] == 6
    old_markers = list((OLD / 'rate_state_v9').glob('**/reports/run_starts/*.json'))
    v10_markers = list((V10 / 'native_lifetime_next/runtime/reports/run_starts').glob('*.json'))
    markers = list((BASE / 'runtime/cpu_regression/run_starts').glob('*.json'))
    assert (len(old_markers), len(v10_markers), len(markers)) == (352, 108, 6)
    for item in read(REPORT / 'PRESERVATION.json')['preserved']:
        assert digest(item['path']) == item['sha256']
    plan = read(cpu['plan']['path'])
    assert digest(cpu['plan']['path']) == cpu['plan']['sha256']
    for item in [plan['binary'], plan['config'], plan['tool']]:
        assert digest(item['path']) == item['sha256']
    clean_path = V10 / 'native_lifetime_next/runtime/reports/LIFETIME_CLEAN.json'
    old_clean = {(r['program'], r['R']): r for r in read(clean_path)['tasks'] if r['policy'] == 'U'}
    records = []
    for row in cpu['tasks']:
        assert row['status'] == 'PASS_NORMAL_FUNCTION_STATE_CPU_C0_NOT_TIMING_QUALIFICATION'
        directory = Path(row['output'])
        for name, expected in row['hashes'].items():
            assert digest(directory / name) == expected, ('RAW_CHANGED', directory, name)
        a = old_clean[row['program'], row['R']]
        s = row['seu']; jobs = s['overwrite_forward_calls'] + s['overwrite_undo_calls']
        assert s['overwrite_tap_terms'] == 912 * jobs
        assert s['overwrite_source_bits'] == 130 * jobs
        assert s['overwrite_fold_bit_writes'] == 200 * jobs
        assert s['representation_overwrite'] == 1 and s['fold_phi_mismatch_words'] == 0
        assert row['cycles'] == a['cycles'] and row['instructions'] == a['instructions']
        records.append({
            'program': row['program'], 'R': row['R'], 'cycles': row['cycles'],
            'instructions': row['instructions'], 'IPC': row['IPC'],
            'lookup_issues': s['lookup_issues'], 'forward_jobs': s['overwrite_forward_calls'],
            'undo_jobs': s['overwrite_undo_calls'], 'full_fold_jobs': jobs,
            'full_fold_jobs_per_lookup': jobs / s['lookup_issues'],
            'full_fold_jobs_per_observed_C0_cycle': jobs / row['cycles'],
            'tap_terms': s['overwrite_tap_terms'], 'fold_bit_writes': s['overwrite_fold_bit_writes'],
            'host_cpu_seconds': row['host_cpu_seconds'],
        })
    buf = io.StringIO(newline='')
    writer = csv.DictWriter(buf, fieldnames=list(records[0]))
    writer.writeheader(); writer.writerows(records)
    csv_path = REPORT / 'CPU_NORMAL_ACTIVITY.csv'
    if csv_path.exists():
        assert csv_path.read_bytes() == buf.getvalue().encode(), 'EXISTING_ACTIVITY_CSV_DIFFERS'
    else:
        with csv_path.open('x', newline='') as f:
            f.write(buf.getvalue())
    save('CPU_NORMAL_ACTIVITY.json', {
        'status': 'PASS_ACTUAL_CPU_NORMAL_ACTIVITY_NOT_FINITE_SERVICE_MODEL',
        'records': records, 'CPU_raw_report': ref(cpu_path),
        'units': 'Logical operations in the observed C0 execution, not energy/area/clock delay',
        'interpretation': 'II * jobs <= cycles is only aggregate capacity on this fixed observed stream. Burst occupancy, operand availability and feedback can still require stalls. No exact CPI causal decomposition.',
    })

    times = []
    for p in sorted((BASE / 'runtime').rglob('*.time')):
        lines = p.read_text().strip().splitlines()
        assert lines, ('MISSING_TERMINAL_TIME', p)
        user, system, rss = lines[-1].split()
        times.append({'file': ref(p), 'seconds': float(user) + float(system), 'rss_kib': int(rss)})
    new_seconds = sum(t['seconds'] for t in times)
    roots = {str(p): kib(p) for p in [OLD, V10, ROOT]}
    combined_gib = sum(roots.values()) / 1048576
    original_whole_gib = kib(Path('/home/youns/workspace/ele548-project')) / 1048576
    # The old charged legacy snapshot is not the full original workspace,
    # which also contains large pre-existing reference datasets/builds.
    prior_gate_path = V10 / 'native_lifetime_next/reports/FINAL_GATES.json'
    prior_resources = read(prior_gate_path)['resources']
    legacy_gib = 20.54370880126953
    assert abs(prior_resources['combined_gib'] - prior_resources['v9_v10_worktrees_gib'] - legacy_gib) < 1e-9
    free_gib = shutil.disk_usage(ROOT).free / 1024**3
    assert new_seconds < 3600 and roots[str(ROOT)] < 192 * 1024
    assert combined_gib < 8 and combined_gib + legacy_gib < 34 and free_gib >= 10
    combined_coreh = 11.171808333333335 + new_seconds / 3600
    global_coreh = 76.57026388888889 + new_seconds / 3600
    assert combined_coreh < 16 and global_coreh < 108
    save('FINAL_GATES.json', {
        'status': 'PASS_V11_FUNCTIONAL_PILOT_AND6_CPU_REGRESSIONS_NOT_FAULT_CPU_OR_COST_QUALIFICATION',
        'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'actual_global_CPU': 3475, 'global_CPU_cap': 3475, 'CPU_remaining': 0,
        'count_derivation': {'legacy_before_v9': 3009, 'all_v9_including_R2': 352, 'v10': 108, 'v11': 6},
        'new_CPU_clean': 6, 'new_CPU_fault': 0, 'new_EDA': 0,
        'resources': {'new_recorded_coreh': new_seconds / 3600,
                      'v9_v10_v11_recorded_coreh': combined_coreh,
                      'global_recorded_coreh': global_coreh,
                      'combined_worktree_GiB': combined_gib, 'inherited_charged_legacy_GiB': legacy_gib,
                      'charged_legacy_plus_three_worktrees_GiB': combined_gib + legacy_gib,
                      'whole_original_workspace_GiB_NOT_CHARGED_LEGACY': original_whole_gib,
                      'free_GiB': free_gib, 'root_sizes_KiB': roots},
        'resource_scope': 'Actual new three-worktree allocated du plus prior charged-legacy20.5437088013GiB snapshot; not a fresh full legacy-directory audit or a cap on all original reference data/builds. Original whole-directory du reported separately. Recorded GNUtime is process-tree accounting, not serverwide usage.',
        'inherited_legacy_charge_evidence': ref(prior_gate_path),
        'retained_finalizer_failure': ref(BASE / 'runtime/closeout_A1/EXECUTION.json'),
        'timefiles': times, 'CPU_report': ref(cpu_path), 'CPP_gate': ref(REPORT / 'CPP_GATE.json'),
        'pilot_summary': ref(REPORT / 'PILOT_SUMMARY.json'),
        'manifest': ref(REPORT / 'LOGICAL_STATE_MANIFEST.json'),
        'budget_field_correction': 'prepare_gate.budget cpu_simulations_dispatched=0 is a preparation-only helper field. CPU_REGRESSION resources inherits this field; it is not a global/actual count. Authoritative dispatch counts are immutable run_starts markers and the terminal CPU report checked above. Original records retained unchanged.',
        'not_done': ['Fault CPU overwrite replication', 'Independent input/owner evaluation',
                     'Finite overwrite stages/ports/latency/backpressure',
                     'Hardware cost or safety qualification'],
        'full_research_goal': 'ACTIVE_NOT_COMPLETE',
    })

    # No RNG draw, new workload, simulation, source edit or event-contract change.
    task_path = V10 / 'native_lifetime_next/runtime/configs/LIFETIME_FAULT.lock.json'
    fault_report_path = V10 / 'native_lifetime_next/runtime/reports/LIFETIME_FAULT.json'
    original_tasks = read(task_path)['tasks']
    reference_fault = read(fault_report_path)
    assert reference_fault['status'] == 'PASS' and reference_fault['actual_runs'] == 72
    proposed = []
    for original in original_tasks:
        if original['policy'] != 'U':
            continue
        t = json.loads(json.dumps(original))
        t['label'] += '.V11_OVERWRITE'
        t['phase'] = 'V11_EXISTING_OWNER_FAULT_REPLICATION'; t['policy'] = 'OVERWRITE'
        t['output'] = str(BASE / 'runtime/cpu_fault_next' / t['label'])
        args = t['config_arguments_without_schedule']
        args[args.index('--representation') + 1] = 'overwrite'
        assert args[args.index('--scheme') + 1] == 'P0'
        assert args[args.index('--repair-cycles') + 1] == '0'
        for key in ['program_binary', 'control', 'expected_stdout', 'schedule']:
            assert digest(t[key]['path']) == t[key]['sha256']
        t['proposed_command'] = [plan['binary']['path'], '--outdir=' + t['output'],
                                 plan['config']['path'], *args, '--schedule', t['schedule']['path']]
        proposed.append(t)
    assert len(proposed) == 12
    six_clean_seconds = sum(r['host_cpu_seconds'] for r in records)
    # Two owner replays per clean case and the same declared1.5 planning factor.
    proxy_coreh = 1.5 * 2 * six_clean_seconds / 3600
    save('NEXT12_PROPOSAL.json', {
        'status': 'PREPARED_NOT_AUTHORIZED_NOT_DISPATCHED', 'CPU_gate': ref(cpu_path),
        'source_task_lock': ref(task_path), 'source_fault_report': ref(fault_report_path),
        'new_tasks': proposed, 'new_CPU': 12, 'reserve': 0,
        'requested_global_CPU_cap': 3487, 'current_global_CPU_cap': 3475,
        'requested_v11_recorded_coreh_cap': 2.5, 'current_v11_recorded_coreh_cap': 1,
        'combined_recorded_coreh_cap_unchanged': 16, 'global_recorded_coreh_cap_unchanged': 108,
        'v11_MiB_cap_unchanged': 192, 'combined_worktree_GiB_cap_unchanged': 8,
        'shared_slots_max': 32, 'initial_trial_parallelism': 2,
        'proxy_additional_coreh': proxy_coreh,
        'proxy_basis': {'six_new_clean_actual_seconds': six_clean_seconds, 'planning_multiplier': 1.5,
                        'not_a_guarantee': 'Fault feedback can change host time; inflight reservations required'},
        'purpose': 'Native C0 fault-behavior integration gate using existing6 owners at R1/R8, not independent holdout or hardware timing selection',
        'scope': 'Same conditional raw130 single-SBU absolute tick/site/owner/censoring; no RNG or input changes; original six baselines reused read-only',
        'comparison': 'A/B old same-condition P0 clean/fault; C new six overwrite clean; D proposed overwrite fault. Report per-program B-D and contrasts to every original protected baseline. n2 is exploratory.',
        'future_unapproved': '126 new-input/independent-owner CPU evaluation plus6 reserve from earlier OptionB not included. Finite cost implementation requires its own gate.',
        'dispatch_rule': 'Do not run these commands until user explicitly enlarges the CPU cap and the new budget amendment is recorded.',
    })
    build = read(REPORT / 'CPU_BUILD.lock.json')
    compiler_version = subprocess.check_output([build['compiler'], '--version'], text=True).splitlines()[0]
    save('software.lock.json', {
        'status': 'ACTUAL_SOFTWARE_AND_PRODUCER_BINDING',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'branch': subprocess.check_output(['git', 'branch', '--show-current'], cwd=ROOT, text=True).strip(),
        'python': {'executable': sys.executable, 'version': sys.version.split()[0]},
        'compiler': {'path': build['compiler'], 'version': compiler_version},
        'gem5': {'version': '25.1.0.1', 'upstream_pin': 'c8222cc67a399bfc01e8658dd14b30d5bfd634f9',
                 'reviewed_R2_patch': ref(OLD / 'rate_state_v9/r2/runtime/configs/source.lock.json'),
                 'binary': build['binary'], 'build_lock': ref(REPORT / 'CPU_BUILD.lock.json'),
                 'build_info_date_scope': 'Reused original build-date object; SHA and new link/execution records are authoritative'},
        'new_tool_installation': 'NONE', 'new_EDA_execution': 0,
        'functional_source_lock': ref(REPORT / 'SOURCE_A2.lock.json'),
        'analysis': ref(BASE / 'tools/analyze_functional.py'), 'closeout': ref(Path(__file__)),
    })
    table = '\n'.join(
        f"|{r['program']}|{r['R']}|{r['cycles']:,}|{r['IPC']:.6f}|{r['full_fold_jobs']:,}|{r['full_fold_jobs_per_lookup']:.4f}|"
        for r in records)
    report = f'''# V11 overwrite: 정확성·작은 pilot·CPU 정상 회귀 완료

## DONE

**IMPLEMENTED/TESTED RESULT:** 기존 결과를 보존한 새 `codex/v11-overwrite` worktree/producer에서 update-time fold overwrite를 pinned plain TAGE 전체 모델에 통합했다. Hash/history 길이/provider/훈련/update schedule은 유지하고 actual source로 fold를 갱신하는 방식만 바꿨다. S*=346bit와 P0/P_ED/P_ECC/P_TMR, frequent/periodic parity·exact direct를 그대로 유지한다.

- C++ gate: 정상150,000 branch의 prediction/index/tag/provider/훈련·상태/RNG 대조, speculative128,000 lookup,124,512 undo check,512 outstanding, rollover2회, fold200 SBU·raw130 age, snapshot/signed/atomic gate 통과.
- 실제 HW1 design trace2개: fixed role/offset16 case,104 fault replay+8 direct-fold 비노출 행,112 정상 window 대조 통과. C++ 결과이며 SPEC CPU 바이너리 실행이나 CPU 성능 결과가 아니다.
- 새 gem5 ELF: header consumer3개를 다시 컴파일하고 원본 object1,513개를 읽기 전용 재사용해 별도 링크했다. 원본 ELF SHA와 원본 archive를 보존했다. 새 ELF SHA는 `{build['binary']['sha256']}`다.
- 승인된 reserve6을 정상 CPU 회귀에 사용했다. 전부 출력·cycles·instructions·canonical state fingerprint·predictor RNG gate 통과. 새 overwrite fault CPU는0회다.

## 정상 CPU 결과와 관측 작업량

**IMPLEMENTED/TESTED RESULT:** 모든 아래 cycles는 기존 같은 입력/R의 정상 TAGE와 같았다. Native L0/C0 결과이므로 finite update latency/ports가 실현된 성능 이득으로 해석하지 않는다.

|프로그램|R|cycles|IPC|forward+undo full-fold 작업|작업/lookup|
|---|---:|---:|---:|---:|---:|
{table}

**NEW DERIVATION:** full-fold 한 번은130 unique source bit,912 tap term,200 fold bit 쓰기다. Lookup에서 source reduction을 없앤 대신 forward와 speculative undo 모두에서 전체 reduction을 수행한다. 이 수치는 논리 작업량이며 PPA/energy 또는 CPI의 정확한 원인 분해가 아니다. 평균 service 수용 조건만으로 burst·dependency·queue 깊이를 결정할 수 없다. 전체 수치는 `CPU_NORMAL_ACTIVITY.csv`다.

## 오류 pilot이 뒷받침하는 것과 남긴 반례

**IMPLEMENTED/TESTED RESULT:** overwrite의 fold8 case는 추가 오예측0과 clean prediction fingerprint 일치를 보였다. Raw8 case에는 SHORT-INT의 +2, LONG-SPEC의 +1이 남았다. P0의 raw SHORT-INT 네 case는 +501/+79/+10/+6, LONG-SPEC은 +123/+16/+8/+1이었다. 해당 raw SBU에서 ECC/TMR은0이었다. Direct의 helpful −1도 제거하지 않았다. 모든 기준선의 owner별 signed 값은 `PILOT_SUMMARY.json`에 있다.

이는 고정 actual stream의 관측이다. 오류 folded register가 다음 update에서 덮어써진다는 gate와 이후 CPU 피해가 항상 사라진다는 주장은 다르다. Source 자체 손상, rollback으로 재진입하는 retained raw 손상, 잘못된 학습은 남을 수 있다. 사건 RNG·per-bit rate·MCU 통계나 독립 표본 CI를 새로 만들지 않았다.

## VERIFIED ASSUMPTIONS / NOT DONE

이번 CPU는 synchronous native C0로 full overwrite를 수행한다. 실제 유한 request/service stage·operand sampling·visibility·port/II/backpressure를 구현하지 않았다. Source/FIFO/native pending의 기존 stage-fit 가정도 유지한다. 기존 pipeline과 직렬 latency 결과의 의미는 변경하지 않았다.

Overwrite fault CPU, 새로운 independent input/owner evaluation, 유한 overwrite timing, metadata/retention 전체 노출, 비용 Pareto·실제 하드웨어 우위는 미완료다. 새 RTL/Cadence/SPICE/TCAD 실행은0이며 hardware-qualified 후보도0이다. 전체 연구 goal은 active다.

## 보존·실패·실행 예산

원본 transport/source·binary·archive와 새 functional 입력 SHA가 맞았다(`PRESERVATION.json`). Test oracle 속도 문제로 종료143인 A1, include 누락, CPU build 두 단계 수정, 잘못된 `--version` probe 실패를 모두 유지했다(`RETAINED_FAILURES.json`). 실패를 무영향 오류나 성공으로 바꾸지 않았다. 원시 로그/명령/GNUtime은 runtime의 각 EXECUTION에 있다.

Global CPU는 `3009+352+108+6=3475/3475`이고 잔여0이다. 새 recorded 사용량은 {new_seconds/3600:.6f}coreh, v9+v10+v11 합계 {combined_coreh:.6f}/16, global {global_coreh:.6f}/108coreh다. 세 worktree는 {combined_gib:.6f}/8GiB이며 이전 과금 legacy snapshot20.543709GiB를 더하면 {combined_gib+legacy_gib:.6f}/34GiB, free {free_gib:.3f}GiB였다. 전체 원본 폴더의 현재 크기 {original_whole_gib:.3f}GiB는 기존 대용량 자료/build까지 포함하며 과금 legacy snapshot과 다르다. 이번에 legacy 전체를 새로 감사했다는 주장은 하지 않는다. Package 추가 뒤에는 다시 확인한다. Shared32slot/build2 상한을 지켰다.

최초 finalizer는 전체 원본 크기를 과금 legacy와 혼동해 assertion에서 중단했다. 해당 source/exit1을 `runtime/closeout_A1`에 보존하고 범위를 위와 같이 명시해 수정했다. CPU/정상 activity 원시 결과는 변경하지 않았다.

`prepare_gate.budget()`의 CPU0 field는 준비 단계용 값이다. CPU 회귀의 resource snapshot에 상속된0도 실제 실행 수가 아니다. 원본 기록은 보존하고 terminal report와 immutable run_starts marker를 실제 count로 검증했다(`FINAL_GATES.json`).

## 다음 결정

**DESIGN HYPOTHESIS:** fold의 recurrent 오류 지속성은 끊되 lookup의 큰 reduction을 피할 수 있다는 가설을 functional 수준에서 계속 시험할 가치가 있다. Update/undo의 full reduction 부담 때문에 최종 비용 개선은 아직 미확정이다.

기존 같은 raw130 owner/tick/site의 overwrite12 replay를 다음 최소 대조로 준비했다. 새 cap은3475→3487(+12), reserve0, v11 recorded cap1→2.5coreh이며 combined16/global108·disk192MiB/8GiB는 유지한다. 여섯 새 정상 실행의 실제 host 시간을 근거로 한1.5배 planning proxy는 추가 {proxy_coreh:.3f}coreh다. 상한 보장이 아니므로 초기2 trial 뒤 실제 시간·예약을 재검토한다. 기존 baseline A/B와 새 C/D의 B−D 및 모든 기존 보호법 대비 대조를 보고한다. 이는 기존 owner replication이며 독립 평가로 부르지 않는다.

이12회도 새 CPU cap 승인 전에는 실행하지 않는다. 구체적인 입력·seed가 아닌 기존 owner·schedule SHA·명령은 `NEXT12_PROPOSAL.json`에 있다. 이 통합 gate 뒤 finite update/source 비용을 별도 구현·검증하고, candidate/resource를 고정한 후 independent 평가로 간다. 성능 우위를 미리 가정하지 않는다.
'''
    with (REPORT / 'FINAL_REPORT.ko.md').open('x') as f:
        f.write(report)
    actions = f'''# 필요한 사용자 결정

**현재 DONE:** overwrite C++ gate·실제 trace pilot·새 gem5 producer·정상 CPU6회 gate와 보존/실행 예산 검산. 상세는 `FINAL_REPORT.ko.md`다. 실패했던 command·수정·raw는 `RETAINED_FAILURES.json`과 참조 EXECUTION에 남았다. 미해결 compiler/tool/license/path 의존성은 없다.

**BLOCKER:** 실행 명령 실패가 아니라 사용자가 승인한 global CPU3475회 상한에 도달했다. 새 fault trial은 발행하지 않았다. 상한을 우회하거나 기존 결과를 지우지 않는다.

**요청:** 준비된 same-condition overwrite12회 개발 replication에 한해 global cap3475→3487(+12), v11 recorded time cap1→2.5coreh를 승인할지 결정한다. Combined16/global108coreh, v11 192MiB/합산8GiB·전체34GiB/free10GiB, 공유32slots는 그대로다. 실제 six-normal 기반 추가 host planning proxy는 {proxy_coreh:.3f}coreh이고 보장값은 아니다. 초기2 trial 후 재예측하며 자동 retry/reserve는 없다.

**정확한 계획/명령:** `NEXT12_PROPOSAL.json`. 동일 기존6 program/owner×R1/R8의 raw130 single-SBU만 사용한다. Source/timing/rate/종료 censoring/RNG 계약을 바꾸지 않는다. 기존 여섯 baseline·새 정상6회를 재실행하지 않는다. 새 입력 독립126회와 reserve6, finite timing 변형은 이 요청에 포함하지 않았다.

**승인 없이 계속 가능한 일:** 현재 결과·source·manifest·provenance 검토와 finite timing 설계. 새로운 CPU/EDA 실행은 하지 않는다. 전체 연구 목표는 미완료이며 active로 남긴다.
'''
    with (REPORT / 'USER_ACTIONS_REQUIRED.md').open('x') as f:
        f.write(actions)
    print(json.dumps({'status': 'PASS_BOUNDED_V11_CLOSEOUT', 'actual_global_CPU': 3475,
                      'new_recorded_coreh': new_seconds / 3600,
                      'next12_proxy_coreh': proxy_coreh,
                      'next12_dispatched': 0}))

if __name__ == '__main__':
    main()
