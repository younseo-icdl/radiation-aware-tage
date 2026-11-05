# Overwrite 후보의 구현 경계와 다음 비용 검증

## 관측 → 경쟁 설명 → 최소 변경

**IMPLEMENTED/TESTED RESULT — 이전 결과:** v10 native C0 R1/R8 비교에서 exact direct는 무보호 대비 피해를 줄였지만 dijkstra·sha1에서는 ECC/TMR과 동일 cycles였고, qsort에서 parity보다 느린 조건이 있었다. 같은 비용·동일 기능을 가진 전체 하드웨어의 우위를 입증한 결과가 아니다. 원본은 [v10 보고서](/home/youns/workspace/ele548-project-v10/native_lifetime_next/reports/FINAL_REPORT.ko.md)이며 다시 작성하지 않았다.

**DESIGN HYPOTHESIS:** direct의 전체 source reduction을 lookup에서 history 변경 시점으로 옮기면 lookup fan-in을 줄일 수 있다. 반대로 full-fold 쓰기와 speculative undo가 비용을 지배하면 불리하다. 두 설명을 함께 평가한다.

**SOURCE FACT — 새 구현:** [overwrite.hpp](/home/youns/workspace/ele548-project-v11/overwrite_v11/src/overwrite.hpp)는 실제 raw-history forward/undo 후 실제 저장 source만으로 21개 fold/200bit를 덮어쓴다. 기존 recurrent fold update를 먼저 실행하지 않는다. 정상 hash/history 길이/provider/훈련/RNG/update schedule은 유지한다. 저장된 fold는 lookup과 HOLD에서 그대로 읽으며, 오류 여부를 injector나 golden model에 묻지 않는다.

기존 S*=raw130+path16+fold200=346bit와 P0/P_ED/P_ECC/P_TMR을 보존한다. frequent parity와 periodic incremental parity k64, exact direct는 별도 비교군이다. Overwrite는 일곱 번째 추가 후보다. HW1은 읽기 전용이다.

## 무엇을 회복하고 무엇을 남기는가

**IMPLEMENTED/TESTED RESULT:** C++ gate에서 모든 200 fold SBU가 lookup/HOLD 동안 남고 다음 실제 history 변경에서 일관된 fold로 덮어써졌다. raw130 모든 age는 실제 source로 사용되었고 고정 forward stream의 active window에서 결국 나갔다. 512개 speculative record와 rollback 중 SEU, finite-buffer rollover, snapshot/deep-copy·signed MSB·atomic duplicate rejection을 시험했다.

**SOURCE FACT / 제한:** source 자체가 틀리면 잘못된 source를 일관되게 접는다. raw/path·table·rollback retention을 golden으로 고치지 않는다. active window에서 나간 raw 손상이 undo로 다시 들어오는 사례도 시험해 그대로 보존했다. Fold register를 정상화해도 이전 오예측으로 생긴 table 학습, 잘못된 CPU 경로, 미래 피해까지 모두 회복했다는 뜻은 아니다.

**IMPLEMENTED/TESTED RESULT — 작은 fixed-stream 시험:** 두 실제 HW1 design trace의 raw/fold×4 고정 위치·offset, 총16 case에서 104 fault replay와8 direct-fold 비노출 행을 구분했다. 112 정상 window의 prediction fingerprint/miss 수는 일치했다. Overwrite의 fold8 case는 추가 오예측0과 정상 prediction fingerprint 일치를 보였다. Raw8 case에서는 SHORT-INT의 +2와 LONG-SPEC의 +1이 남았다. exact direct의 −1 helpful 사례도 유지했다. 전체 owner별 signed 결과는 `PILOT_SUMMARY.json`이다.

이8 fold case 중 주입 직후 control7개는 conditional,1개는 unconditional이었다(`PILOT_EVENT_CONTEXT.json`). 따라서 모두 unconditional 앞에 주입되어 자동 무해해졌다는 설명은 맞지 않는다. 그래도 이 관측은 다른 fold bit/PC/provider·speculation·군집에서 무해함을 증명하지 않는다. Fixed actual stream에는 CPU wrong-path feedback이 없다. 사건당10,000 control 뒤 tail은 관측하지 않았다. 확률 표본이나 방사선 rate·MCU 실험으로 표기하지 않는다.

## CPU 통합에서 비용으로 계산하지 않은 것

**IMPLEMENTED / ASSUMPTION:** 새 gem5는 native L0/C0 P0/LEGACY에서만 overwrite를 허용한다. 실제 source를 읽고 fold를 계산하지만 callback 안에서 동기적으로 완료된다. 유한 update stage·port·operand availability·queue·backpressure를 구현한 결과가 아니다. 계산을 끝낸 뒤 debt만 청구하는 timing 변형도 추가하지 않았다.

따라서 정상 cycles가 기존 TAGE와 같으면 알고리즘·동작 회귀 통과를 뜻한다. 정상 overhead가 물리적으로0이라는 결과, stage-fit/clockability 증명, 읽기 latency 숨김의 성능 이득 또는 하드웨어 승자 판정으로 해석하지 않는다. 기존 v6 pipeline/직렬 latency 실험의 의미도 변경하지 않는다.

**NEW DERIVATION — 작업량:** 이 설정에서 full-fold 한 번은 130개의 고유 active-source bit를 이용한 912 tap term과200 fold bit 쓰기다. 이는 logical operation 계수이며 실제 C++의 반복 read 수, 독립 포트 수, XOR cell 개수, 면적·에너지와 같지 않다. CPU별 실제 forward+undo 횟수와 lookup 비율은 `CPU_NORMAL_ACTIVITY.csv`로 기록한다. `source_transition_jobs`는 finish callback 수이므로 새 overwrite recomputation 수로 대체하지 않는다.

고정 관측 stream에서 단일 service unit의 평균 수용 조건 `II×Njobs ≤ cycles`는 필요조건 수준이다. 동일 cycle에 몰리는 squash/undo, FIFO 깊이, source dependency, lookup visibility는 이 평균만으로 검증되지 않는다. 지연이 CPU의 branch stream을 바꿀 수도 있다. Counter 합을 CPI의 정확한 인과 분해로 쓰지 않는다.

## 다음 최소 실험과 진행 조건

1. 실제 six-normal CPU gate가 모두 통과한 뒤, 기존 raw130 single-SBU owner/tick/site의12 overwrite replay를 개발 replication으로 비교한다. 기존 A/B와 새 C/D를 연결해 프로그램별 B−D와 모든 기존 보호법 대비 signed contrast를 낸다. 이는 독립 input/owner holdout이 아니다. `NEXT12_PROPOSAL.json`의 상한 변경이 승인되기 전에는 발행하지 않는다.
2. Overwrite가 functional 피해를 충분히 끊는다면 finite source/update timing을 구현한다. Lookup pipeline과 journal/RMW 변경을 분리하고 recurrent/direct/overwrite에 같은 lookup L/II/port 조건을 적용한다. 동기 callback을 전부 직렬화하거나 overwrite만 병렬화해 결론 내리지 않는다. 기존 보호 경로의 encode/check/vote/repair도 동일 비용 경계에서 비교해야 한다.
3. 실제 stage 구현에서는 source operand가 사용 가능한 시점에 sample되고, 재계산이 끝난 뒤 fold가 공개되어야 한다. 이전 결과가 다음 PC/history에 필요하면 forwarding/bypass 또는 stall이 필요하다. speculative undo의 순서를 보존하고 ID/epoch/freshness·취소·stale 응답을 시험한다. 새 queue/snapshot/control storage의 폭·깊이는 구현에서 정한 뒤 manifest에 넣는다. 여기서 임의의 폭/서비스 보장을 미리 발명하지 않는다.
4. Candidate/resource/input/owner 규칙을 고정한 뒤 독립 평가한다. SOURCE와 WHOLE은 구분하고 기존 event RNG namespace·time/rate·종료 censoring을 유지한다. 비용까지 포함한 paired 이득이 없으면 실패 조건과 비용 하한을 결과로 남기고 다음 최소 변경을 고른다.

**NOT DONE:** overwrite fault CPU, 독립 평가, finite overwrite service, 전체 source/retention/control 노출, 새로운 latency/resource Pareto, 실제 하드웨어 안전성/우위. TCAD/SPICE/Cadence/RTL은 실행하지 않았다. 새로운 알고리즘의 최초 제안·novelty를 주장하지 않는다.
