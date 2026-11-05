"""Final interpretation is generated from actual terminal report/CSV evidence."""
from v5_common import ROOT,write,sha,used_cpu
from v5_statistics import paired_interval
import csv,json,statistics,collections,datetime
F=ROOT/'rate_state_v5/results';R4=ROOT/'rate_state_v5/runtime';R5=ROOT/'rate_state_v5/runtime_r5'
def load(p):return json.loads(p.read_text())
def csvrows(name):return list(csv.DictReader((F/name).open()))
def report(name):
 d=load(R5/'reports'/(name+'.json'));assert d['status'] in ['PASS','COMPLETED_WITH_FAILED_RUNS'];return d
required=['SOURCE','WHOLE','SHORT_CONTROL','METADATA','PERSISTENT_CLEAN','PERSISTENT_FAULT','EVALUATION_V3_CLEAN','EVALUATION_V3_FAULT']
for n in required:report(n)
assert load(F/'ANALYSIS.lock.json')['status']=='MEASURED_AGGREGATION'
summary=csvrows('CPU_PAIRED_SUMMARY.csv');abcd=csvrows('CPU_ABCD.csv')
evalphase='EVALUATION_V3_FAULT';ev=[r for r in summary if r['cohort']==evalphase]
programs=sorted(set(r['program'] for r in ev));policies=['PARITY64','BATCH_DIRECT','BATCH_STRAT16']
def f(x,n=3):return '' if x is None or x=='' else f'{float(x):.{n}f}'
def summary_table(rows):
 s='|program|조건|방법|valid/planned|정상 overhead %|B−D 순이득 %p [95% CI]|오류 후 추가 비용 %p(A기준)|\n|---|---|---|---:|---:|---:|---:|\n'
 for r in rows:
  s+=f"|{r['program']}|{r['scenario']}|{r['policy']}|{r['n_valid_pairs']}/{r['n_scheduled']}|{f(r['normal_overhead_pct'])}|{f(r['mean_gain_pp'])} [{f(r['gain_CI_low'])}, {f(r['gain_CI_high'])}]|{f(r['mean_residual_pp'])}|\n"
 return s
evaltext=summary_table([r for r in ev if r['policy']!='NATIVE'])
macro=[]
for scenario in sorted(set(r['scenario'] for r in ev)):
 for policy in policies:
  rs=[r for r in abcd if r['cohort']==evalphase and r['scenario']==scenario and r['policy']==policy]
  groups=[[float(r['net_gain_pp']) for r in rs if r['program']==p and r['pair_valid']=='True'] for p in programs]
  valid=all(len(x)==20 for x in groups)
  if not all(groups):
   macro.append(dict(scenario=scenario,policy=policy,equal_program_mean_gain_pp=None,full_pairs=False,
     interpretation='At least one program has no complete pair. Macro undefined; failed programs not dropped.'))
   continue
  mean=statistics.mean(statistics.mean(x) for x in groups)
  # Each owner is paired before averaging; independently resample owners per program.
  import numpy as np
  rng=np.random.default_rng(3515480001)
  samples=[rng.choice(x,size=(10000,len(x)),replace=True).mean(axis=1) for x in groups if x]
  means=np.mean(samples,axis=0)
  macro.append(dict(scenario=scenario,policy=policy,equal_program_mean_gain_pp=mean,CI_low=float(np.quantile(means,.025)),CI_high=float(np.quantile(means,.975)),
       full_pairs=valid,interpretation='nominal paired bootstrap; survivor-only if any owner failed; no multiplicity correction or device-rate inference'))
write(F/'EVALUATION_MACRO.json',dict(status='ACTUAL_INDEPENDENT_EVALUATION',programs=programs,conditions=macro,
 criteria='engineering budgets, not laws or calibrated statistical power guarantees',fully_qualified_hardware_candidates=0))
(F/'INDEPENDENT_EVALUATION.ko.md').write_text('''# 동결 후 독립 CPU 평가

IMPLEMENTED/TESTED RESULT: 개발과 다른 입력3개, 공개 추가 프로그램2개, 조건당20개의 독립 event owners, 방법4개를 사용했다. 원래 basicmath binary80 실행은 지원 안 되는 x87 명령으로 정답 검증에 실패했다. 첫 binary64 수정도 musl float printf의 x87 경로에서 잘못된 memory access로 실패했다. 두 번의 구체적 호환 수정 후 binary64+integer-only 출력의 별도 basicmath_sseio를 사용했다. 모든18004 cubic 출력,1002 integer sqrt,angle 변환은 native에서 독립 확인했고 gem5는 전체 stdout byte 일치를 요구했다. 이 파생 프로그램들을 원본 SPEC 또는 MiBench 공식 점수로 표시하지 않는다.

원본18회 clean 중16개 성공 실행을 동일 입력/producer로 재사용하고 새 파생 프로그램4회를 추가했다. 합친20행을20개의 새 실행이라고 세지 않는다. fault 결과를 본 뒤 predictor/tap/resource를 바꾸지 않았다. 최종 fault800회는 EVALUATION_V3 namespace이며 original/V2 실패는 보존했다.

A=정상 reference, B=오류 reference, C=정상 policy, D=오류 policy. 총 순이득은 B−D이며, 오류에 따른 추가 피해 감소는 (B−A)−(D−C)이다. 이 DID에는 표현별 민감도·노출·timing 상호작용도 포함되므로 복구 메커니즘만을 분리한 인과 추정치가 아니다. 각 프로그램/조건에서 동일 owner를 짝지은 뒤 bootstrap10000회, 명목95% CI를 계산했다. 프로그램 macro는 프로그램 동일가중이다. 20owners는 드문 프로그램 실패 확률을 검증할 수 있는 수가 아니며 CI가0을 포함해도 동등성 증명은 아니다. 여러 조건의 CI에는 familywise 보정이 없다.

'''+evaltext+'''
CPU_PAIRED_SUMMARY.csv에는 signed 피해의 경험적 p90/max와 helpful/zero 비율도 기록했다. n4 개발·n2 반복 작업·n20 평가의 표본 분위수를 실제 환경의 상위 tail 확률로 해석하지 않는다. 이 작은 표본의 bootstrap CI는 특히 탐색적이며 paired owner를 task 반복 수만큼 늘리지 않았다.

WHOLE은 명시된 논리 population의 SBU 가속 시나리오이며 타겟 방사선 rate가 아니다. inherited checkpoint/CPU ownership 제외 범위가 남아 완전한 물리 storage 정합 비교도 아니다. 추가 metadata 오류로 실행이 실패한 owner는 cycles를 성공값으로 보간하지 않는다. 표의 valid/planned가 다르면 CI는 성공한 paired owners에만 조건부이고 전체 population의 성능 우위로 발표할 수 없다.
''')

resources='''# 비용과 효과의 손익분기

IMPLEMENTED/TESTED RESULT: 초기 유한 직접 계산형은 원본과 역복원마다 별도 거래를 넣어 qsort 정상 overhead6.35%였다. 실제 BPU squash 경계의 undo count와 마지막 saved path를 하나로 줄여 L2 복원 패킷을 서비스한 뒤 정상 overhead0.54%가 됐다. source operands는 서비스 완료 때 읽고 raw/head/path도 그때 공개한다. 기능을 먼저 수행한 뒤 비용 debt만 청구한 모델이 아니다. 이 비교는 transport의 회복 기능 동등성 및 유한 서비스 대조이며, circular-buffer rewind 발명의 주장은 아니다.

|개발 program|primary lookup 추가0 cycle overhead %|추가1 cycle %|추가2 cycle %|
|---|---:|---:|---:|
'''
clean=csvrows('REPRESENTATION_COMPARISON.csv')
for program in ['qsort_small','dijkstra_small','sha1']:
 def lookup(ident):return next(r for r in clean if r['namespace']=='runtime_r5' and r['program']==program and r['policy']==ident)
 resources+=f"|{program}|{f(lookup('BATCH_DIRECT')['normal_vs_native_pct'],4)}|{f(lookup('BATCH_READ1')['normal_vs_native_pct'],4)}|{f(lookup('BATCH_READ2')['normal_vs_native_pct'],4)}|\n"
resources+='''
ASSUMPTION: primary lookup 추가0은 기존 예측 단계 안에 source read/XOR/tag lookup이 들어간다는 조건이다. 물리 지연0이나 무한 포트를 측정했다는 뜻이 아니다. 추가1cycle에서도 정상2% budget을 넘는 프로그램이 있으므로 후보의 허용 지연은 좁다. source appendL1/undoL2/64slots(단일 non-pipelined server; launch gap1, 실제 append II1/undo II2), 동시에 필요한 BPU undo span/path operand, raw read fanout과 codec/queue ports를 하드웨어에서 입증해야 한다.

직접 계산의21fold raw 기여 수와 source age 수는 STATE_PROFILE에서 얻었다. contributions를 물리 read port 개수로 바꾸지 않는다. GF(2) rank는 PC/path를 고정한 한 lookup의 direction map만의 파생량이지 전체 predictor capacity나 CPU 성능의 척도가 아니다. sparse16은 정보 선택뿐 아니라 tag 혼합도 달라져 충돌 구조도 달라진다.

LOCAL_RATE_BREAK_EVEN.csv는 무오류 비용 C−A와 조건부 사건당 추가 피해 감소 g=(B−A)−(D−C)를 사용한 탐색용 mu≈(C−A)/g를 기록한다. g≤0이면 양의 local crossing을 만들지 않았다. C−A<0인 qsort parity의 개선은 SHAM timing으로 이미 관찰된 scheduling 효과이므로 낮은 rate에서도 radiation 보호가 유리하다는 근거가 아니다. mu가 작지 않으면 선형식을 연장하지 않고 실제 반복 주입 결과를 읽어야 한다. hazard/종료시간의 feedback, 다중 사건, censoring을 무시한 교차점을 실제 운영 rate로 발표하지 않는다.

P_ECC는 동일 prediction check k64지만 모든 RMW 전에 손상된 payload를 정정·확인해야 한다. unchecked state를 새 ECC로 덮어써 정상처럼 만들지 않기 위해 추가 decode를 실제 endpoint에서 수행했다. 따라서 'matched cadence'가 총 decode 작업량 동일이라는 뜻은 아니다. ECC가 오류를 줄여도 이 유지 비용이 CPU 순이득을 넘을 수 있다.

독립 bitcount 정상 실행에서 BAC branchMisspredict는 native3602, exact direct3604, stratum16은8447이었다. 동일 유한 backend의 두 직접 계산형 사이에서 정상 예측 손실이 커진 증거다. 같은 hardware service contract를 쓴다고 hash/정보량 변경이 무료인 것은 아니다. 이 counter는 CPU model의 해당 stage 집계이며 committed branch MPKI와 혼용하지 않는다. 소스 wait 등 activity counters는 겹칠 수 있으므로 CPI를 더해서 분해하지 않는다.

PPA_PENDING: source bits/queue entries/XOR 수는 area/energy/delay 결과가 아니다. storage 수와 비용 Pareto는 논리/CPU 조건부이다. 실제 동일 PDK 비교와 actual switching은 이번 실행 범위 밖이다.
'''
(F/'RESOURCE_BREAK_EVEN.ko.md').write_text(resources)

negative='''# 유리하지 않은 결과와 미해결 조건

1. 초기 direct CPU 산출물은 rollback virtual hook 우회 때문에 무효였다. native 정상 종료만으로 predictor 동등성을 통과했다고 보지 않았다. 고친 R4/R5 gate 결과만 최종 분석에 쓴다.
2. 8tap geometric/stratum의 INT/FP 정상 정확도 손실이 컸다. 단 한 번의16tap 수정 뒤에도 일부 trace의 warning이 남아 추가 seed/parameter 탐색을 하지 않았다. sparse/short32의 정보 감소와 hash 변경 효과를 분리해서 해석한다.
3. 원본의 undo당 유한 source 거래는 정상 CPU budget을 넘었다. 묶음 undo가 이를 줄였지만 lookup에1cycle을 더하면 qsort14.93%,dijkstra8.30% overhead라 primary 이득은 read timing 조건에 민감하다.
4. 포인터 상위 bit 오류와 queue control DUE에서 두 새 구조 모두 실행 실패했다. 이12개 adverse cases 중6개 실패는 선택한 경계 사례의 결과이며 측정 radiation failure probability가 아니다. 실패를 masked/zero-cost로 세지 않았다.
5. original basicmath x87와 첫 binary64-only 호환 수정은 정답/메모리 gate 실패로 보존했다. 성공한 새 출력 포트는 별도 workload 이름/ELF/namespace를 쓴다.
6. profile JSON 형식의 orchestration 오류로 dispatch가 일시 중지됐다. 집계기와 검증된 prefix resume를 수정했고 이미 끝난 실행을 새 결과로 재사용하지 않았다.
7. whole enumerated population은 common CPU ownership/checkpoint 제외를 유지한다. Native backing retention과 새 direct journal의 물리 ownership inventory가 정합하지 않아 이 결과만으로 whole-chip reliability/physical storage 우위를 결론내릴 수 없다.
8. R28 문헌 참조의 spectrum/FF 이전은 미확인이다. 희소율 계산은 fixed-window partial surrogate이며 p>=2와 추가 storage hazard를0으로 채우지 않는다. mission FIT/실제 소자 rate 또는 우위 교차점을 만들지 않는다.
9. 모든 packet/codec/lookup L/II는 CPU model 계약이다. RTL/PDK/실제 read fanout 및 clockability는 검증하지 않았다.
'''
(F/'NEGATIVE_RESULTS.ko.md').write_text(negative)

hardware='''# HDL 이전 후보 판정과 계약

판정: **현재 fully qualified 새 하드웨어 후보0개.** 아래 두 구조는 조건부 연구 모델이며 '새 승자'로 승격하지 않는다. 포인터/queue DUE의 total transition 부재가 직접 실패 시험에서 확인됐고, primary lookup timing과 전체 물리 storage ownership도 미확정이다. 독립 평가의 평균 cycles가 좋아도 이 안전 gate를 대체하지 못한다.

|구조|정상 예측 함수|조건부 이점|필수 자원과 한계|
|---|---|---|---|
|현재 raw에서 동일 fold를 직접 계산|같은 interface에서는 pinned plain TAGE와 exact; 유한 timing은 speculation을 바꿀 수 있음|재귀 fold 오류 재사용 제거; table/CPU 회복 보장은 아님|raw1130/path16/head11/pending68,queue64×37+49,단일 서버 appendL1/II1·undoL2/II2,lookup 추가0/II1 조건|
|history 위치를 고르게16개씩 고른 직접 계산|hash/정보량이 달라 같은 predictor 함수가 아님|read/XOR 기여 감소 가설; 정상 정확도/정보량 손실 가능|동일 retention/queue;21개의 selected reductions; 새 tap tuning 금지|

먼저 필요한 소프트웨어 gate:11-bit pointer 모든1130..2047 encoding의 유한·안전 주소/복원 동작 정의, queue DUE 때 accepted/completed/cancelled/pending 보존과 bounded recovery/backpressure, pending freshness/epoch/cancel 상태의 total transitions, mid-recovery SEU와 stale saved-path 재유입, metadata atomic multi-bit injection 순서 독립성. host throw/assert는 그 하드웨어 동작의 구현이 아니다. production은 syndrome/parity/freshness/epoch만 사용하고 injector/golden 정보를 읽지 않아야 한다.

하드웨어에서 나중에 확인할 조건: raw 선택/fanout/XOR/tag path가 기존 stage 안에 들어가는지, clock당 queue/control/codec ports, actual BPU undo-span10/path16 입력 가용성과 reduction/service bound<=1000, speculative correction과 append의 순서, reset/flush 도중 재오류 동작, common CPU checkpoint/retention storage mapping. 같은 함수/interface/PDK/PVT/clock/load/constraints와 actual switching을 갖춘 비교가 필요하다. 이번에는 HDL을 작성하거나 Cadence를 실행하지 않았다.

안전 불변식: 프로그램 stdout/정상 종료 보존; 하나의 atomic event는 실제 logical bits만 XOR1회; raw operand는 completion에서 읽음; source 결과는 completion 전 소비하지 않음; finite queue no-drop/보존식; valid ownership 또는 안전 fallback 없이 새 prediction/commit을 공개하지 않음; 종료 pending은 censoring. 현재 마지막의 metadata-invalid 동작을 만족하지 못해 승격을 보류한다.

novelty 한계: direct folding/circular journal/partial history/parity/ECC는 선행 방법이다. 이번 기여 후보는 오류 지속 구조×rate×state lifetime×유한 CPU 서비스의 검증된 조건별 결과와 비용/실패 경계이다. 새 알고리즘의 최초성·실측PPA·칩 reliability 우위는 주장하지 않는다.
'''
(F/'HARDWARE_CANDIDATE_CONTRACT.md').write_text(hardware)

final='''# 두 연구 축의 최종 판정

결론: 재귀 fold를 없애는 표현은 fixed-stream의 오래 남는 오류 피해를 줄였다. 유한한 source 복원 거래를 BPU squash 단위로 묶으면 정상 CPU 비용도 줄일 수 있었다. 그러나 **새 하드웨어 승자는 확정하지 않는다.** metadata-invalid 안전 gate가 실패했고, lookup 추가0cycle과 population ownership의 물리 타당성도 남아 있다.

## DONE — 실행·검증한 것

- 기존 연구/holdout 보존, 별도 `codex/rate-state-v5` branch·runtime/R5 namespace, pinned gem525.1.0.1 exact commit/source/config/ELF/input/owner locks.
- 같은 S*346bits의 P0/P_ED/P_ECC/P_TMR 비교 보존. rate main은 주기 parity와 RMW-safe SECDED를 포함하고 필수 TMR single-event 대조를 유지했다.
- exact direct 정상 equality, raw/helperfold 독립 injection, snapshot/rollback/oddPC, native checksum, finite operand/publication/queue 보존, corrected R4/R5 CPU gates와18개 full-program baseline compatibility.
- 실제 trace C++ single-event·긴 관측창·두 reset diagnostic, 실제 gem5 rate/source/whole-enumerated/repeated-task/short32 대조와 독립 입력/owner 평가.
- A/B/C/D와 paired CI, 정상 비용/추가 오류 피해 분해, 희소 rate의 p0/p1/p>=2 및 missing evidence, 실패와 종료 censoring을 명시했다.

## 독립 평가 — 프로그램별 결과

'''+evaltext+'''
결과를 읽을 때: source-targeted CHARM와 table/추가 metadata를 포함하는 whole-enumerated SBU는 서로 다른 모집단이다. 두 조건의 time compression을 조절해 승자를 고르지 않았다. failure가 있으면 표는 complete paired survivors에만 조건부이며 전체 성능/안전성 우위가 아니다. 정상2%와 실익0.05%p 등의 문턱은 사전 선언한 engineering choices다.

## NOT DONE

타겟 FF/SRAM 방사선 rate/임무 FIT, 원래 basicmath binary80의 gem5 ISA 지원, 전체 CPU physical storage 노출, robust metadata controller, RTL/Cadence/SPICE/PDK와 실제 PPA는 완료하지 않았다. SPEC CPU 배포본을 실행한 점수가 아니라, HW1의 SPEC2006 유래 traces와 공개 MiBench 파생 native programs의 CPU model 결과다. TCAD는 사용하지 않았다.

## VERIFIED MODEL ASSUMPTIONS

2GHz/500pscycle의 같은 O3/cache/memory 설정, RNG548와 별도 사건 role namespaces, 원본 kernel/입력 SHA, native stdout equality, completion-only source publication 및 finite queue를 실행 자료로 확인했다. 하드웨어에서 해당 L/II/ports가 가능하다는 가정이나 문헌 SRAM의 FF 이전을 검증한 것은 아니다.

## BLOCKERS / NEXT

외부 설치·license·SPEC 구매 때문에 이번 소프트웨어 분석이 막힌 것은 아니다. R28 PDF§§2.1/2.2/2.4는 참조율 감사의 선택적 보완 자료다. 다음 구조 작업은 먼저 metadata total-transition과 공정하지 않은 물리 ownership 경계를 고친 뒤 새 소프트웨어 gate/독립 평가를 해야 한다. 이후에만 동일 PDK의 실제 read/rollback ports와 lookup stage 비용을 검토할 수 있다. 이 라운드는 두 축과 독립 CPU 평가를 완료한 '현재 조건에서 qualified 새 후보 없음' 결론으로 종료하며 HDL 전에 멈춘다.
'''
(F/'FINAL_DECISION.ko.md').write_text(final)
actions='''# 사용자 행동과 의존성

지금 필요한 설치/권한/파일 업로드: **없음.** 소프트웨어 두 축과 독립 평가는 완료했다. 전역 환경·license·sudo·SPEC 설치는 변경하지 않았다.

선택적 문헌 보완: R28 DOI10.3390/electronics13112012, PDF의§§2.1/2.2/2.4와 cross-section 정의/입사 spectrum. publisher PDF403/HTML429 및 collection PDF403의 접근 실패는 runtime/literature/ACCESS.json에 보존했다. 실패한 정확한 HTTP GET 대상은 https://mdpi-res.com/d_attachment/electronics/electronics-13-02012/article_deploy/electronics-13-02012.pdf 이며403 Forbidden이었다. 출판사 HTML 및 collection 경로 두 대안도 실패해 추가 우회를 시도하지 않았다. 접근 제한을 우회하지 않았다. PDF가 없어도 조건부·가속 실험은 끝냈다.

실제 미해결 구현 조건: direct head-invalid/queue DUE의 안전 동작. 재현 명령은 `scripts/v5_r5_metadata.py`의 동결 tasks와 `runtime_r5/configs/METADATA.lock.json`/raw logs에 있다. 현재 namespace는 immutable이므로 그대로 재실행해 덮어쓰지 않는다. 새 프로토콜을 구현하려면 새 producer/namespace에서 모든 encoding·mid-recovery·stale rollback gate부터 수행한다. 이는 사용자 license 요청이 아니라 다음 소프트웨어 설계 과제다.

추가 프로그램 실패: original basicmath_lp64의 unsupported x87와 첫 binary64-only musl printf page fault는 EVALUATION_CLEAN/EVALUATION_V2_CLEAN에 보존했다. 두 구체적 호환 수정 이후 basicmath_sseio가 전체 native stdout equality를 통과했다. 원래 실행의 성공으로 표시하지 않는다.

RTL/Cadence/SPICE/PDK는 사용자 지정으로 보류했다. TCAD는 사용하지 않는다. 실제 PPA/FIT 빈칸에0을 채우지 않았다.
'''
(F/'USER_ACTIONS_REQUIRED.md').write_text(actions)
(F/'START_HERE.ko.md').write_text('''# v5 완료 자료 읽기

먼저 FINAL_DECISION.ko.md, INDEPENDENT_EVALUATION.ko.md를 읽는다. 조건부 두 표현의 이점은 있지만 fully qualified 하드웨어 후보는0개다. 결과를 본 뒤 predictor/tap/resource를 수정하지 않았다.

- 확률/단위: DATA_MODEL_CARD.ko.md, RATE_ANCHORS_AUDIT.json, RATE_REGIME_MAP.csv.
- 상태 지속/비용: STATE_LIFETIME_ANALYSIS.ko.md, RECURSIVE_DELTA_DERIVATION.ko.md, REPRESENTATION_COMPARISON.csv, RESOURCE_BREAK_EVEN.ko.md.
- 실제 CPU/실패: CPU_ABCD.csv, CPU_PAIRED_SUMMARY.csv, CPU_FAILED_PAIRS.csv, EXECUTION_AUDIT.json, NEGATIVE_RESULTS.ko.md.
- 구현 경계/선행연구: STATE_CONTRACT.md, RESOURCE_CONTRACT.json, HARDWARE_CANDIDATE_CONTRACT.md, NOVELTY_EVIDENCE_MATRIX.md.
- 재현: software.lock.json, 각 runtime/configs source/producer/input/owners/task locks, raw reports와 EXPERIMENT_LEDGER/HYPOTHESIS_LOG. 원본과 V2 실패는 보존하고 corrected R4/R5 및 최종 evaluationV3만 성능 해석에 쓴다.

완료 namespace에 같은 명령을 다시 실행해 덮어쓰지 않는다. 새 구현/평가에는 별도 namespace와 독립 입력/seed가 필요하다. 경량 ZIP은 기존 사용자 workspace 위에 이어받는 overlay다. 빌드 ELF/전체 gem5 tree/기존 대형 raw archive는 SHA와 로컬 경로로 참조한다. HDL/PDK/Cadence/SPICE는 실행하지 않았고 TCAD는 사용하지 않는다.
''')
write(F/'FINAL_INTERPRETATION.lock.json',dict(status='TWO_TRACKS_AND_CPU_EVALUATION_COMPLETE_NO_QUALIFIED_HARDWARE_WINNER',
 at=datetime.datetime.now(datetime.timezone.utc).isoformat(),qualified_new_candidates=0,conditional_models=['BATCH_DIRECT','BATCH_STRAT16'],
 evidence_summary_sha256=sha(F/'CPU_PAIRED_SUMMARY.csv'),evaluation_sha256=sha(R5/'reports/EVALUATION_V3_FAULT.json'),
 metadata_gate=load(R5/'reports/METADATA_DECISION.json'),recorded_core_hours=used_cpu()/3600,stop='Authorized two-track synthesis complete; stop before HDL.'))
print('Final reports generated from actual completed cohorts;0 hardware-qualified candidates')
