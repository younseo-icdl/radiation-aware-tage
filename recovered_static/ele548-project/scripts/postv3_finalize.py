"""Close a rejected-extension round only after actual G0/G2 evidence and audit."""
import collections
import csv
import subprocess
from postv3_common import *

decision=json.loads((OUT/'reports/G2_DECISION.json').read_text())
assert decision['status']=='REJECT_GROUPED_EXTENSIONS_RETAIN_N1_REFERENCE','Independent evaluation/conditional next work remains'
start=json.loads((OUT/'BASELINE_SNAPSHOT.json').read_text())
for p,h in start['old_files'].items():assert sha(ROOT/p)==h,('OLD_FILE_CHANGED',p)
source=json.loads((OUT/'configs/source.lock.json').read_text())
for p,h in source['sources'].items():assert sha(ROOT/p)==h,('NEW_SOURCE_CHANGED',p)
for p,h in source['transport'].items():assert sha(ROOT/p)==h,('TRANSPORT_CHANGED',p)
producer=json.loads((OUT/'configs/PRODUCER.lock.json').read_text())
assert sha(runner.BINARY)==producer['binary_sha256'] and sha(runner.CONFIG)==producer['config_sha256']
pin=subprocess.check_output(['git','-C',ROOT/'third_party/gem5-postv3','rev-parse','HEAD'],text=True).strip()
assert pin==source['pin']
for name in ['tage.cc','tage.hh','tage_base.cc','tage_base.hh']:
    assert sha(ROOT/'third_party/gem5-postv3/src/cpu/pred'/name)==sha(ROOT/'third_party/gem5/src/cpu/pred'/name)
allrows=[]
for name in ['CPU_GATE','CLEAN','G2']:
    d=json.loads((OUT/'reports'/f'{name}.json').read_text())
    assert d['status']=='PASS' and d['completed']==d['planned']==len(d['tasks'])
    for t in d['tasks']:
        assert t['status']=='PASS' and t['producer_binary_sha256']==producer['binary_sha256']
        for f,h in t['hashes'].items():assert sha(ROOT/t['output']/f)==h,('RAW_ARTIFACT_CHANGED',t['output'],f)
    allrows+=d['tasks']
faults=json.loads((OUT/'reports/G2.json').read_text())['tasks']
paired={(t['program'],t['scenario'],t['owner'],t['id']):t for t in faults}
all130=[t for t in faults if t['id']=='P_ALL130']
for t in all130:
    n=paired[t['program'],t['scenario'],t['owner'],'N1']
    assert all(t[k]==n[k] for k in ['cycles','instructions'])
    assert all(t['seu'][k]==n['seu'][k] for k in ['canonical_base_state_hash','predictor_rng_hash','predictor_rng_draws'])
g0=json.loads((OUT/'reports/G0_ACCEPTANCE.json').read_text())
g2=json.loads((OUT/'reports/G2_ANALYSIS.json').read_text())
assert g0['status']=='PASS'
audit=dict(status='PASS',old_files_preserved=len(start['old_files']),old_commit=start['commit'],old_branch=start['branch'],
    current_branch=subprocess.check_output(['git','branch','--show-current'],text=True).strip(),
    actual_CPU_runs=len(allrows),native_or_protocol_failures=0,SHAM_clean_diagnostics=3,
    actual_faulted_grouping_runs=144,independent_new_evaluation_run=False,
    source_binary_config_raw_hashes_verified=True,pinned_TAGE_algorithm_unchanged=True,
    ALL130_exact_N1_fault_pairs=len(all130),
    recorded_host_core_hours=used_cpu()/3600,checkpoint_core_hours=32,RTL_Cadence_SPICE_TCAD_used=False,
    retained_build_history=['BUILD_1_PREFLIGHT_STOP.json','BUILD_2_FAILURE.json'],
    cpp_log_sha256=sha(OUT/'reports/PIPELINE_CPP_FINAL.log'))
write(OUT/'reports/FINAL_AUDIT.json',audit)
write(OUT/'reports/software.lock.json',dict(status='ACTUAL_GATED_AND_AUDITED',parent_commit=start['commit'],
    implementation_commit=subprocess.check_output(['git','rev-parse','583fa74a7'],text=True).strip(),
    pin=pin,producer=producer,source_lock_sha256=sha(OUT/'configs/source.lock.json'),
    development_input_lock_sha256=sha(ROOT/'continuation_v3/runtime/configs/design_inputs.lock.json'),
    round_lock_sha256=sha(OUT/'configs/round.lock.json'),old_research_modified=False,
    physical_measurements=False,rate_calibrated=False,final_audit_sha256=sha(OUT/'reports/FINAL_AUDIT.json')))

phase=list(csv.DictReader((OUT/'RECOVERY_PHASE_COST.csv').open()))
phase_groups=collections.defaultdict(list)
for r in phase:
    if r['completion']=='DRAIN_END':phase_groups[r['variant'],r['phase']].append(r)
phase_summary=[]
for (variant,name),rr in sorted(phase_groups.items()):
    phase_summary.append(dict(variant=variant,phase=name,completed_intervals=len(rr),
        mean_elapsed_cycles=sum(float(r['elapsed_cycles']) for r in rr)/len(rr),
        mean_unique_source_wait=sum(int(r['wait_source']) for r in rr)/len(rr),
        mean_unique_drain_wait=sum(int(r['wait_drain']) for r in rr)/len(rr),
        mean_unique_response_wait=sum(int(r['wait_response']) for r in rr)/len(rr),
        mean_unique_retire_wait=sum(int(r['wait_retire']) for r in rr)/len(rr)))
write(OUT/'reports/PHASE_SUMMARY.json',dict(status='ACTUAL_COMPLETED_DRAIN_INTERVALS',rows=phase_summary,
    caveat='Interval means are event/phase conditioned; not independent owner samples. Different wait types overlap. Initial refill/useful partial-bank execution are separate CSV intervals, not lost cycles.'))

lines=['# Post-v3 최종 판단','',
    'N1을 다음 하드웨어 검토의 최소 참고 후보로 남긴다. 정한 development screen을 통과한 새 grouping 후보는 없다. 이는 동등성 증명이나 다른 입력에서의 개선 가능성 부정이 아니다.', '',
    'G0 clean scheduling 진단 → G1 phase/CPU wait 계측 → G2 안전한 경계 변경의 고정144회 비교를 완료했다. 새 구조의 우위를 만들기 위해 검사 주기·주입률·resource를 바꾸거나 seed를 계속 늘리지 않았다.', '',
    '|프로그램|P0_FINITE|N1/P3/SHAM clean cycles|N1 clean delta (%)|', '|---|---:|---:|---:|']
for r in g0['programs']:lines.append(f"|{r['program']}|{r['A']}|{r['N1']}|{r['clean_delta_pct']:+.4f}|")
lines+=['','SHAM_WAIT가 parity 유지·검출·복구 없이 같은 정상 실행 결과를 재현했다. 주기적 응답 대기가 read/training과 speculative 실행의 상대 시점을 바꾼 효과다. RNG_at_read는 그 시각까지 진행한 update 수의 관측값이며, 전체 committed RNG draw/hash는 P0/N1에서 같았다. 이 clean 효과를 radiation recovery 이득에 포함하지 않는다. 실제 ROB retirement 순서의 PC/microPC/identity prefix로 정렬했다. 상세 최초 차이는 CLEAN_BASELINE_AUDIT.ko.md에 있다.', '',
    '|안전 grouping|N1 대비 평균 추가 이득 (pp)|최악 프로그램/조건 이득 (pp)|새 평가 screen|', '|---|---:|---:|---|']
for r in decision['results']:lines.append(f"|{r['variant']}|{r['mean_gain_vs_N1_pp']:+.5f}|{r['worst_program_scenario_gain_pp']:+.5f}|{'통과' if r['qualifies_for_new_evaluation'] else '미통과'}|")
lines+=['','|보호법|조건|qsort gain pp|dijkstra gain pp|SHA1 gain pp|','|---|---|---:|---:|---:|']
for r in g2['summaries']:
    pp=r['per_program'];lines.append(f"|{r['variant']}|{r['scenario']}|{pp['qsort_small']['mean']:+.5f}|{pp['dijkstra_small']['mean']:+.5f}|{pp['sha1']['mean']:+.5f}|")
lines+=['','최소 실질 이득0.05pp, 프로그램/조건 평균 회귀 허용0.05pp, normal2%와 residual mean2pp budget을 실행 전에 고정했다. 세 프로그램 각 고정 입력1개, SBU/CHARM, design-only owner4개다. 분석의 bootstrap은 탐색용이며 workload 모집단 CI가 아니다. clean 차이, fault increment, total gain 및 difference-of-differences를 PROMOTION_ABLATION.csv에 분리했다. 마지막 통계도 순수 물리 인과량은 아니다.', '',
    'P_ALL130은24개 fault pair 모두에서 N1과 cycles·instructions·canonical base state·RNG가 같았다. wrapper가 있다는 사실만으로 오류 후 성능 차이가 생긴 것은 아니다. 16/130은 CHARM qsort에서+0.11478pp였으나 SBU qsort에서는−0.07097pp였다. 좋은 조건만 골라 채택하지 않았다. 최악 program/scenario 평균 residual은 N1 약0.12927pp에서16/130 약0.03814pp로 줄었지만, 사전 residual budget2pp는 N1도 충족했고 표본4개로 tail 우위를 주장할 수 없다. 더 엄격한 residual 목표를 정하면 별도 사전 명세와 새 평가가 필요하다.', '',
    '|보호법|완료 phase|interval n|평균 elapsed cycles|평균 unique source wait|평균 unique drain wait|', '|---|---|---:|---:|---:|---:|']
for r in phase_summary:lines.append(f"|{r['variant']}|{r['phase']}|{r['completed_intervals']}|{r['mean_elapsed_cycles']:.3f}|{r['mean_unique_source_wait']:.3f}|{r['mean_unique_drain_wait']:.3f}|")
lines+=['','phase trace는 reset/initial committed refill, 최초 handoff, partial-bank 실행, 후속/final promotion, 재시작 및 종료 censoring을 구분한다. raw trace의 N1 stage-count/mask 필드는 사용되지 않으므로 CSV에서 refill과 handoff 상태로 qualified count/admission을 명시적으로 환산했다. Raw queue count는 observer가 ECC를 정정하거나 오류 처리를 앞당기지 않도록 decode하지 않은 snapshot이다. RESET 시점 in-flight 수는 마지막 관측치이며 drain 경계는 그 frontend poll의 실제 predHist 크기다.', '',
    'elapsed에는 유효한 실행도 포함된다. unique wait는 해당 tick에서 frontend/retirement 기회가 거부된 관측치이며 서로 겹칠 수 있다. 기존 평균92.43 drain counter 차이를 전체 손실·제거 시 speedup·엄밀한 상한으로 쓰지 않았다. 기능 효과와 비용 효과가 섞이는지를 실제 grouping의 최종 cycles로 확인했다.', '',
    'G3의 비차단 mask/version promotion은 이번 screen이 새로운 복잡도를 정당화하지 않아 구현하지 않았다. 최초 handoff와 기존 safe drains를 모두 유지했다. G4는 directed coverage 검증만 유지했으며 detector/recovery를 동시에 바꾸지 않았다. 동일 word2-bit parity blind spot, SECDED3+ 및 correlated-copy 한계는 남는다. 이 결과는 더 강한 검출이 불필요하다는 증명이 아니다.', '',
    '저장 bit 수와 서비스 모델은 logical contract다. N1은 base65370 + common finite engine7240 + controller72 =72682 cells, STAGED grouping은22 cells가 추가된다. 실제 CPU metadata의44bit/live record 소유권·retention capacity와 codec/scoreboard ports는 여전히 별도 비용이다. 같은 L/II/capacity와 detector-time reset/ECC 예외 경로를 유지했으며 C1을 실제 코드별 물리 지연으로 해석하지 않는다.', '',
    '다음 하드웨어 검토에는 N1 k64, hot FIFO64×57+49 control, ready credits64×55, reservation22와 arbiter1, 346-bit history 및23 check words의 read/write·XOR/check ports가 필요하다. dependent source RMW L/II와 metadata lifetime/ports를 실제 구현에 바인딩하고, 같은 library/PVT에서 얻은 지연으로 CPU 평가를 다시 해야 한다. 기존 RESOURCE_AND_HARDWARE_CONTRACT.md의 sampling/repair 예외·protected CPU ownership 가정을 유지한다. 물리 우위는 미확정이다.', '',
    '현재 비교점은 L=1, II=1, hot capacity64, pending reference capacity1024다. 중단·새 입력·경쟁이 없고 해당 service unit을 소유하면 hot FIFO의 drain bound는64×max(L,II) cycles다. 재주입·repair hold·새 work·arbitration이 있으면 이 조건부 bound를 그대로 쓰지 않으며 mission WCET로 해석하지 않는다. operand는 completion에서 읽어 effect를 공개하고 retirement credit을 준수한다. 실제 issue-captured multi-cycle SRAM RMW와 동일하다고 주장하지 않는다.', '',
    f"감사: 실제 CPU {len(allrows)}회(별도 clean SHAM3회 포함), native/protocol 실패0. 이전 파일 {len(start['old_files']):,}개 hash를 보존했다. 초기 build 중단/오류는 로그로 남겼으며 실패한 build를 CPU producer로 승격하지 않았다. 기록된 host CPU 시간은 {used_cpu()/3600:.3f}core-hours이며 준비/분석 bookkeeping은 별도다.", '',
    '범위는 공개 MiBench qsort/dijkstra/SHA1의 전체 프로그램 실행이며 공식 SPEC CPU 점수가 아니다. 기존 v3/G6 평가를 독립 holdout으로 재사용하지 않았다. 실질 후보가 선정되지 않아 새 독립 평가를 추가하지 않았다. HDL/RTL/Cadence/SPICE/TCAD 전에 종료한다. 추가 데이터·라이선스 요청은 없다.', '',
    '재검토: CLEAN_BASELINE_AUDIT.ko.md, RECOVERY_PHASE_COST.csv, PROMOTION_ABLATION.csv, reports/G2_ANALYSIS.json, reports/G2_DECISION.json, reports/FINAL_AUDIT.json 및 reports/software.lock.json. 새 라운드에서 정책을 바꾸면 새 input/owner와 사전 freeze가 필요하다.']
(OUT/'FINAL_DECISION.ko.md').write_text('\n'.join(lines)+'\n')
(OUT/'NOVELTY_AND_LIMITS.ko.md').write_text('# 신규성 및 한계\n\n이번에는 새 아키텍처를 채택하지 않았다. 주기 검사, promotion grouping, graceful degradation 또는 hybrid 보호 자체를 발명으로 주장하지 않는다. 기존 v3 NOVELTY_MATRIX.md의 AMD history cohesion·BOOM metadata·CLEAR·ICCD prior art 범위를 유지한다. 기여는 clean timing 통제, 실제 handoff/promotion 대기 분해와 음의 비용/성능 결과다.\n\n동일 source/detector/k/resource에서 safe boundary만 변경했다. 비차단 mask/version protocol과 stronger-detect-only를 구현한 것으로 표기하지 않는다. logical cell·operation·assumed service를 area/energy/PPA/FIT로 변환하지 않았다. 표본 max로 p99/WCET를 주장하지 않는다.\n')
(OUT/'USER_ACTIONS_REQUIRED.md').write_text('# 필요한 사용자 행동\n\n현재 software 결과를 검토·재집계하기 위해 추가 dataset, SPEC 설치본, network 권한 또는 license가 필요하지 않다. G0/G2와 후보 기각 판단을 완료했다.\n\nHDL/PDK 단계는 시작하지 않았다. 이후에는 같은 library/PVT에서 storage/metadata ports와 실제 L/II를 정하고 측정한 비용으로 CPU 비교를 갱신해야 한다. TCAD를 의존성으로 두지 않는다.\n')
manifest_dir=OUT/'sources';manifest_dir.mkdir(exist_ok=True)
entries=[]
for t in allrows:
    if t['scenario']!='zero' or t['id']=='SHAM_WAIT' or t['id'] in [r['variant'] for r in entries]:continue
    p=ROOT/t['output']/'logical_manifest.json'
    entries.append(dict(variant=t['id'],path=str(p.relative_to(ROOT)),sha256=sha(p),
        bits=t['total_bits'],source_lock_sha256=sha(OUT/'configs/source.lock.json')))
write(manifest_dir/'manifest.json',dict(status='ACTUAL_LOGICAL_MANIFEST_INDEX',entries=entries,
    base_manifest=dict(path='sources/predictor_logical_state_manifest.json',sha256=sha(ROOT/'sources/predictor_logical_state_manifest.json')),
    selected_scope=dict(path='sources/protection_scope.lock.json',sha256=sha(ROOT/'sources/protection_scope.lock.json'),bits=346),
    diagnostic_fields='Observer hashes/counters/provenance never drive the production controller and are excluded from hardware storage',
    retained_CPU_interface='44 logical bits per live record plus original BranchInfo/checkpoints; protected CPU ownership/ports/lifetime assumption remains explicit',
    grouping_configuration='Static circuit grouping parameter, not a runtime adaptive selector',
    rate='Original conditional CHARM K205:9 stress at1e-6/core-cycle, not measured target rate; SBU locations use frozen selected words'))
(OUT/'CURRENT_STATE.md').write_text('# Current authoritative state\n\nG0→G2 completed. FINAL_AUDIT passed; original research/costaware-v3 outputs and184,410 files preserved. CPU gate39 + clean18 + SHAM3 + grouping144 executions passed. Historical build/initial-source statuses describe earlier preparation only.\n\nNo grouped extension passed the predeclared selection screen. N1_k64_reference remains the conditional hardware reference. G3 mask/version and G4 stronger detector implementation were not started. No new independent holdout was represented as completed.\n\nRead FINAL_DECISION.ko.md, CLEAN_BASELINE_AUDIT.ko.md, RECOVERY_PHASE_COST.csv, PROMOTION_ABLATION.csv, reports/software.lock.json and sources/manifest.json. Stop before HDL/PDK; no further jobs are required by this completed round.\n')
print('Post-v3 software round audited; retain N1 reference; no HDL. CPU runs',len(allrows))
