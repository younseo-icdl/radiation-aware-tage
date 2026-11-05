# ELE548 진행 상태·사용자 준비·남은 실험 — 2026-10-12

후속 갱신: E3 CPU logicalFI/protection/speculation/hold gate38 cases와 실제52-run pilot 완료; 고정 main4092+latency687 실행 중. Flying Laptop detection-time stress2880 완료. 최신 상세는 `E3_INTEGRATION_REPORT.ko.md`, `FLYING_TIMING_REPORT.ko.md`. 아래 E3 미구현 항목은 이 갱신 전 상태다. CERN method 원문 접근 제한은 USER_ACTIONS_REQUIRED.md에 기록했으며 CPU/CHARM/시간모델 작업을 계속한다.

## 현재 위치

**E0/E1, E2 SBU/CHARM holdout 및 공개 3-program O3 clean baseline 완료 → E3 CPU 주입·speculation/rollback·latency 비교가 다음 단계**다. E2에서 8184 trials, 실행 실패 0이며 S*는 raw/path + folded 346 bits로 유지했다. 세 보호법의 C++ 결과는 `E2_REPORT.ko.md`, 실제 CPU clean 결과는 `E3_PUBLIC_CLEAN_BASELINE.ko.md`에 있다. CPU SEU 성능 저하, Cadence PPA 및 최종 보호법 순위는 아직 없다.

이 문서는 현재 실행 증거를 종합한 요약이다. 원 결과는 `VALIDATION_STATUS.json`, `STAGE0_REPORT.md`, `REPEATED_INJECTION_REPORT.ko.md`와 각 CSV/log에 있다. 원본 handoff의 TODO/실패 보고와 혼동하지 않는다.

## 이미 확정된 연구 조건

- 주 predictor는 pinned gem5 v25.1.0.1의 **plain TAGE**. Gshare는 재현/통제용이다. 기본 알고리즘과 update schedule을 임의 축약하지 않는다.
- 먼저 single-event로 상태별 영향을 측정해 **같은 보호 범위 S***를 고른다. P0와 **P_ED(parity+skip/relearn), P_ECC(SECDED+repair), P_TMR(vote+repair)** 세 복구법을 모두 비교한다.
- C++ bulk fault injection → gem5 O3 CPU 성능 → 동일 PDK의 RTL/Cadence 상대 비용 → 실제 latency를 CPU 모델에 반영한다.
- 공개 방사선 자료가 식별하는 부분과 가정한 timing/location을 구분한다. target 28nm 실측 SEU율은 연구 시작의 필수 조건이 아니다. E4의 상대 PPA에도 target per-bit SEU율이 필수는 아니다.
- TCAD는 사용 불가·제외. Cadence는 뒤로 미루고 SEU/C++ 및 CPU 준비를 우선한다. TAGE-SC-L, Geant4/mission FIT, 새 보호법은 현재 기본 범위가 아니다.
- HW1은 원본을 유지하고 trace를 연구 입력으로 사용한다. gem5 CPU 실행에는 별도 실제 application binary/input을 사용한다. **지금 HW1 실험에 SPEC 설치는 필요 없다.** E3는 공개 프로그램으로 진행할 수 있다.

## 완료·부분 완료·미실행

| 항목 | 상태 | 증거와 범위 |
|---|---|---|
| 원본 자료/환경/소프트웨어 고정 | 완료 | 원 ZIP 118개 및 source 18개 hash, user-local venv/gem5, GCC11, 정확한 gem5 commit |
| Gshare·plain TAGE 정확성 | 완료 | Gshare 200k, TAGE shared-upstream differential 150k branches, state/RNG/update schedule 검사 |
| logical-bit injection | 완료 | 65,370 sites; signed counter, atomic MCU, deep-copy snapshot, raw/folded 독립 주입, rollover 검사 |
| Flying Laptop | audit/replay 생성 완료 | 2129 raw / 2055 distinct / 74 duplicate extra. Detection stream이며 target bit-rate 추정은 아님 |
| CHARM | K 모델·주입 pilot 완료 | 6T 205:9, 8T 142:5; 각각 60 trials. K source-informed, 공간/시간 mapping은 가정 |
| CERN | 취득/MD5/전수 parser 완료, 모델 의미 검토 남음 | p29MeV, p0.9MeV, Ar1050MeV. Grouping/sentinel/singleton completeness 확인 전 physical footprint/rate fitting 안 함 |
| HW1 workload 가용성 | 확인 완료 | 40 traces, 그중 SPEC2006 유래 long 20개. 현재 실험은 SHORT-INT-1/SHORT-FP-1의 실제 구간 |
| single-event P0 pilot | 초기 작은 시험 완료 | 240 trials, 실패 0. 이후 6 traces의 M0 3600 + CHARM 2160 design trials 완료 |
| Poisson 반복 주입 | 구현·작은 시험 완료 | 96 runs + 1 재현 run PASS; 258 events / 268 bit XOR operations. 연속 state, rate는 events/conditional branch |
| gem5 O3 실행환경 | 완료 | v25.1.0.1 debug, X86 single-core/thread, coupled frontend/plain TAGE, native와 checksum 1321703870693 일치 |
| 공개 application CPU baseline | native 독립 정답 및 O3 clean 완료 | 공식 MiBench qsort/dijkstra/SHA-1, 동일 static ELF 정답·exit 일치. 실제 cycles/IPC/committed MPKI 확보. E3_PUBLIC_CLEAN_BASELINE.ko.md |
| S* 선정·동결 | E1 design 완료, E2 holdout 완료 | 5760 design + warmup sensitivity 후 raw/path + folded 346 bits/23 words 동결. Holdout 결과로 재선정하지 않음 |
| TAGE의 P_ED/P_ECC/P_TMR | C++ 구현·holdout 완료 | 정상 동등성, 실제 검출/정정/repair/refill, 추가 storage 노출, 8184 trials. E2_REPORT.ko.md |
| gem5 CPU SEU hook/보호 성능 | 미구현/미실행 | tick scheduling, speculation/rollback, 보호 latency 연결과 CPU clean/faulty 비교 남음 |
| selected-scope RTL·Cadence PPA | 미실행 | primitive RTL 시작 코드가 있으나 selected-scope C++↔RTL 검증과 실제 PPA는 없음 |
| E5 통합/최종 결론 | 미실행 | E1/E2, CPU 성능, 실제 비용 및 불확실성 결과를 모아 결론 |

ASan은 runtime 부재로 미통과이며 Valgrind lifecycle은 0 errors/0 leaks PASS다. ASan 보완은 선택 사항이고 현재 실험을 막지 않는다. Cadence command/PDK 참고 경로 탐지는 license checkout 성공이 아니다. SPEC application은 미설치·배포본 미보유 상태이며 공개 workload E3를 막지 않는다.

## 사용자에게 필요한 확정·준비

**지금 E2와 공개 workload CPU 준비를 시작하는 데 필수로 미제공된 파일·설치본은 없다.** 이미 합의한 연구 범위를 다시 승인받을 필요도 없다. 다음 항목은 요구사항 확인 또는 결과를 보고 검토할 항목이다.

E2 본실험은 이미 완료했다. 이후 남은 목록에서 E2 codec/controller/SBU·CHARM holdout 항목은 completed evidence로 읽는다. E3는 fault-free 공개 application baseline 이후 CPU-level injection을 별도로 수행한다. C++의 ΔMPKI에 cycles/IPC를 임의로 환산하지 않는다.

| 항목 | 언제/무엇을 확인하는가 | 기본 진행 |
|---|---|---|
| 사용 자료 표기 | 사용자 확인 완료 | HW1의 CBP 및 SPEC2006 유래 trace로 명시. 실제 SPEC application binary 실행과 구분하며 추가 교수님/SPEC 확인을 현재 gate로 요청하지 않음 |
| 서버 사용 제한 | 제한 없음, 사용자 확인 완료 | E1은 비용 검사 후 4 workers/고정 표본수를 사용. 변경된 course 일정만 별도 확인 |
| S*와 보호 granularity | E1 design 결과와 한계를 검토 | raw/path + folded 346 bits/23 words가 동결됨. 추가 parity/ECC/replica/controller bits는 E2에서 포함하고 holdout으로 다시 고르지 않음 |
| CPU workload 범위 | 정상 실행·분기 특성·실행 비용 검증 후 선택 프로그램/입력/ROI가 연구 목적에 맞는지 검토 | Codex가 공개 프로그램 2~3개부터 source/input/license/binary/ROI를 고정. SPEC은 필요시 별도 확장 |
| E4 조건 | Cadence 재개 전에 사용할 PDK/library/PVT/clock/load/storage 구현과 측정 범위 검토 | 기존 ASIC flow를 별도 연구 경로에서 참고. Macro가 없으면 동일 표준셀 storage slice 비교로 시작 가능 |
| SPEC access | SPEC application을 실제 gem5에서 실행하려는 경우에만 기관 사용 권한·버전·배포본 경로 준비 | 지금 새 SPEC 구매/설치를 요구하지 않음. HW1의 SPEC 유래 trace는 이미 사용 가능 |
| 과목 제출·상담 | 제출/상담 여부 및 일정 변경을 실제 강의 공지와 확인 | 인계 자료에는 Oct20 전 상담, Oct22 proposal, Dec3 progress, Dec17 talk, Dec21 report/source archive. 제출 완료 여부는 현재 알 수 없음 |

C++ tests, RNG/주입 schedule, parser, native output, gem5 config/rollback/통계, RTL equivalence와 tool logs는 Codex가 검증·보존한다. 사용자에게 bit마다 수동 검증이나 global package 설치를 맡기지 않는다. 사용자 검토에는 같은 S*/input/CPU 조건의 비교인지, 실제 결과와 가정이 분리됐는지, 제출 범위에 맞는지가 핵심이다.

## 남은 실험 전체 목록

### E1 — 어떤 상태를 보호할지 결정

1. **입력 구간과 통계 계획 고정.** HW1 trace의 design/holdout workload 또는 disjoint 구간, seed, instruction 범위와 hash를 고정한다. CPU application holdout과 trace holdout은 별도다. 같은 program의 다른 구간을 독립 application이라고 부르지 않는다.
2. **Warmup·관측창 검증.** 정상 예측률/학습상태의 안정성을 확인한다. 같은 single-event post-event 길이를 확보해서 late injection의 짧은 follow-up 편향을 제거한다. 끝까지 차이가 남으면 censoring을 기록한다.
3. **상태별 single-event 측정 확대.** bimodal/ctr/tag/u/raw-path/folded 여섯 field, raw-direction vs path 및 index/tag folds를 분리해 harm/help/net, first effect, window별 영향과 end state 차이를 측정한다. Inactive table entries도 노출에 유지한다.
4. **표본 불확실성과 노출 가중치.** Event-trial 단위·workload별 confidence를 계산하고 per-event 민감도와 B_j/B 기반 contribution을 따로 보고한다. 후속 branch를 독립 sample로 세지 않는다. Main n/budget은 파일럿 분산·runtime와 목적 precision으로 미리 고정한다.
5. **S* 동결.** Design 결과와 구현 가능성을 근거로 scope와 payload/codeword grouping을 동결한다. 평가 결과로 다시 scope를 고르지 않는다.

완료 기준: 선정 이유, 논리 bits/manifest, design/holdout, 관측 길이·precision·예산이 재현 가능하게 기록됨. 후속 E1 design은 fixed 5760 trials와 explicit warmup sensitivity를 완료해 scope를 동결했다. Stationary warmup 일반화는 주장하지 않는다.

### Fault model — source shape/time와 반복 사건

6. **SBU와 CHARM 6T/8T 비교.** 동일 event intensity와 동일 expected bit-flip intensity를 별도 비교한다. K를 곱해 bit-rate를 이중 계산하지 않는다. 현재 96-run pilot은 equal-event-rate engineering smoke만 완료했다.
7. **반복 rate/repair interval sensitivity.** Continuous state에서 사건 간격과 정상 learning/복구 시간이 겹칠 때 누적 영향을 측정한다. Primary rate sweep과 가정·단위를 고정한다. 반복-run이 통계 단위이며 같은 event stream의 paired scheme 비교를 유지한다.
8. **CERN semantic qualification와 footprint mapping.** Grouping 방법, sentinel, singleton completeness를 검토한 뒤 조건별 군집을 사용한다. K>=3, codeword crossing, interleaving/replica separation 가정을 검증하고 sensitivity로 비교한다. 원 source coordinate를 target PDK micrometer로 직접 환산하지 않는다.
9. **Flying Laptop timing sensitivity.** 실제 timestamp 순서 replay와 time-shuffle/필요시 variable-rate baseline을 비교한다. Duplicate preserve/collapse 해석과 time scaling을 기록한다. 다른 출처의 K와 결합하면 factorized synthetic scenario이고 실측 joint model이 아니다.

완료 기준: 각 모델의 source fact, 독립성·시간·공간 가정, 경계 정책, source/profile uncertainty, 단위/비교 denominator와 결과가 분리됨. 현재 추가 radiation dataset 업로드는 필요 없다.

### E2 — 같은 S*에 세 복구법

10. **P_ED 구현.** 실제 parity mismatch에서 faulty candidate 제외 → fallback → reinit/relearn. History scope면 정의한 reset/refill와 in-flight/epoch 규칙까지 포함한다. Injector/golden을 detector에 전달하지 않는다.
11. **P_ECC 구현.** SECDED check/correct, writeback/scrub, DUE fallback과 bandwidth를 구현한다. Code capability를 넘는 오류는 실제 decoder 결과로 남긴다.
12. **P_TMR 구현.** 세 storage copies, majority, 정상 update와 repaired feedback/cadence를 구현한다. 같은 bit의 두 replica 오류와 서로 다른 bit 오류를 구분한다.
13. **기능 검증.** 각 clean 모드의 의도한 정상 동등성, lookup/update/aging/reset/refill/repair 처리, parity/ECC/replica bits 자체 오류, repair 중 재오류와 검출 불가 사례를 검사한다. Protection manifest에 추가 storage/control을 넣거나 제외 범위를 명시한다.
14. **Holdout 보호 비교.** Same base-state events의 conditional 비교와 모든 added storage까지 포함한 population exposure를 별도 실행한다. C++ accuracy/회복/잔여 상태·failure와 clean overhead를 모두 보존한다.

완료 기준: 세 방식 모두 같은 scope에서 동작·검증하고 holdout 평가까지 완료. 제공 codec/voter 단위시험을 이 완료 결과로 대신하지 않는다.

### E3 — gem5 CPU 성능

15. **대표 workload 준비와 clean baseline.** 공개 프로그램 2~3개의 source/input/argv/compiler/ELF/output validation/ROI를 고정하고 동일 native/gem5 결과를 검사한다. 이 작업은 E1과 병행할 수 있다. 실제 SPEC binary/input을 확보하면 별도 SPEC 조건을 추가한다.
16. **P0 tick-based hook·주입 smoke.** Stable logical IDs, separate RNG, zero/one/repeated 사건, same-tick 순서와 atomic MCU를 검증한다. P0 기반 작업은 S* 선정 전에도 가능하다.
17. **Speculation·squash·state 처리.** Raw/folded 독립 주입이 upstream의 정상 rollback에 어떻게 반영되는지 검사한다. Predictor checkpoint가 완전히 저장되지 않으면 warmup을 매 run 재실행한다.
18. **세 보호법 CPU 연결.** E2의 실제 check/fallback/repair transaction과 response/ready/hold/redirect 지연을 연결한다. Cadence 전에는 latency 가정의 sensitivity 결과로 표시하며 arbitrary misprediction penalty 변경으로 대체하지 않는다.
19. **CPU clean/faulty matrix.** P0/ED/ECC/TMR × clean/faulty × workloads/models/seeds. 같은 CPU clock/cache/width/input/ROI에서 cycles, IPC, committed-branch MPKI, frontend stall, output/failure와 uncertainty를 비교한다. 완료 시간이 길어지면 동일 time intensity에서 추가 노출이 발생하도록 한다.

완료 기준: 대표 application 정답과 CPU FI correctness가 통과하고 clean overhead와 fault loss를 구분한 CPU-model 결과가 있음. 현재 gem5 checksum PASS는 이 본실험 결과가 아니다.

### E4 — 나중에 RTL/Cadence

20. **동일 기능·cycle 계약의 네 RTL.** 동결된 S*에 P0/ED/ECC/TMR의 lookup/update/fallback/repair/ready 인터페이스를 구현하고 C++ reference와 differential한다. RTL simulation 준비는 PPA tool 실행과 구분한다.
21. **같은 PDK cost 측정.** Tool/library/PVT/clock/load/ports/storage/activity 조건을 매칭해 synthesis·place/route·STA·activity-based energy/leakage를 측정한다. Voter/controller/repair/clock와 추가 bits를 포함하고 TMR가 합성에서 합쳐지지 않았는지 확인한다. Saboteur는 synthesis에서 제외한다.
22. **실제 latency/variation 확인.** Stage 내 timing 충족과 추가 cycle 요구를 구분하고 필요한 corner/placement variation을 검증한다. 단순 area 비율을 SEU cross-section 비율로 사용하지 않는다.

현재 사용자 결정으로 Cadence 실행은 유예다. 기존 `/home/youns/ASIC/sram_fft_top`의 activation/flow는 참고하며 기존 DB를 변경하지 않는다.

### E5 — 통합·발표·보고

23. **E4 실제 latency를 E3에 반영.** 가정으로 실행한 CPU sensitivity와 측정 비용을 구분하고 바뀐 경우 해당 CPU 조건을 재평가한다.
24. **모델/비용/Pareto 분석.** 회복효과·clean overhead·면적·delay·operation energy와 confidence를 함께 비교한다. Ranking 변화/불확실성과 무보호가 유리한 경우도 보고한다. Local predictor energy를 whole-CPU energy로 부르지 않는다.
25. **Novelty·보고·재현 bundle.** TAGE 역할별 state/회복 차이와 군집·시간 모델이 보호 선택을 바꾸는 이유를 source/새 결과로 설명한다. Proposal/progress/final slides/report/SOW와 재현 source/config/hash/log를 준비한다. 과목 자료의 제출·서명 여부는 사용자 확인 항목이다.

새 보호법은 위 세 baseline이 완료된 뒤 문헌 확인을 거친 선택 확장이다. TCAD/Geant4/mission FIT/TAGE-SC-L은 이 목록에 새 의존성으로 추가하지 않는다.

## 다음 실행 묶음

E1 결과는 `E1_REPORT.ko.md` 및 `E1_SCOPE_SELECTION.ko.md`를 우선한다. 원 E1 TODO 목록은 실행 계약과 재현 항목으로 유지하며 현재 미완료 목록과 혼동하지 않는다.

1. 같은 S*의 P_ED/P_ECC/P_TMR software controller 및 added-state manifest와 correctness.
2. Design과 분리한 holdout에서 single/repeated event, source model·rate·repair cadence 비교.
3. gem5 O3의 실제 application baseline/SimTick injection/speculation·rollback 및 세 보호법 CPU 성능.
4. 이후 재개할 E4의 실제 latency/cost를 E3에 반영 → E5.

현재 신규 SPEC 또는 external dataset upload 요청은 없다. PDK/Cadence는 계속 유예하며 CPU cycles/IPC를 E1 branch-trace 결과에서 계산하지 않는다.
