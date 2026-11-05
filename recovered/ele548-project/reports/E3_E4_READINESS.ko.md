# E3/E4 진행 조건 — 2026-10-12

## 현재 가능한 작업과 미완료 조건

gem5 O3 실행이 가능하므로 **P0의 E3 주입 hook 구현·검증은 시작할 수 있다.** 다만 실행 가능한 simulator와 세 보호법 비교가 준비된 predictor는 다르다. 이번에 완료한 것은 C++의 continuous-state Poisson/CHARM 주입이다. `reports/REPEATED_INJECTION_PILOT.json`에 96개 run의 결과를 보존했다. **gem5 CPU fault injection은 아직 NOT_RUN**이다.

E4의 interface·시험 stimulus·PDK 조건 준비도 가능하다. 최종 네 설계의 RTL 구현/비용 비교는 S*와 E2의 검출·fallback·repair 동작이 정해진 뒤 진행한다. 사용자의 기존 결정에 따라 이번에는 Cadence를 실행하지 않았다. TCAD는 제외한다.

| 조건 | 현재 증거 | 다음 작업 |
|---|---|---|
| E0 알고리즘/논리 bit 정확성 | PASS, pinned upstream TAGE 및 65,370 sites | 동일 source/config 유지 |
| native / coupled O3 clean 실행 | PASS, checksum=1321703870693 | 이후 hook의 zero-event CPU stats/config/종료를 기존 baseline과 대조 |
| C++ repeated-event injection | PASS, 96 runs + 1 determinism regression | 사전 정의된 rate/model/관측창 sensitivity |
| S* 선정 | UNFROZEN | equal-followup single-event, warmup 안정성, design/holdout input 및 seed 분리 |
| E2 세 보호법 | TAGE에 미구현, primitive tests만 존재 | 같은 S*에 parity+skip/relearn, SECDED, TMR 모두 구현 |
| E3 SimTick 주입 | 미구현/미검증 | tick-based rate, 사건의 원자 주입 및 동일 tick ordering 검증 |
| E3 speculation / rollback | upstream 정상 경로 사용, faulty 동작 미검증 | current raw와 folded 독립 주입, squash의 정상 복원 경로 검증 |
| predictor checkpoint | 지원 증거 없음 | 이 pin의 TAGE/TAGEBase에 serialize/unserialize override 없음. full predictor checkpoint를 사용했다고 주장하지 않고 매 run warmup 재실행 |
| E4 C++↔RTL cycle equivalence | NOT_RUN | lookup/update/repair/ready 계약 및 state transition 검증 |
| E4 PDK/tool/license/PPA | NOT_RUN | 별도 workspace에서 기존 ASIC activation 참고, 실제 checkout/매칭 조건/활동 검증 |
| E4 latency→E3 | 실제 추가 latency 미측정 | ready/hold/redirect 경로 반영. branch misprediction penalty로 대신하지 않음 |

## E3에 연결할 시간 계약

- C++ pilot의 `lambda`는 exposed predictor 전체에 대한 **events / conditional branch**다. branch 간 idle 시간이나 wrong-path 시간을 담지 않는다. 이를 그대로 events/second로 바꾸지 않는다.
- E3는 simulator tick/CPU cycle 기준의 별도 `lambda`를 사용한다. 예를 들어 명시한 events/cycle와 cycles/tick으로 schedule을 만들고, fixed clock에서만 seconds 환산을 한다. 측정 target rate가 아닌 normalized stress라는 provenance는 유지한다.
- pinned `src/sim/eventq.hh`의 EventFunctionWrapper는 callback, 이름, auto-delete, priority를 지원하고 CPU_Tick_Pri는 50이다. 주입 priority와 같은 tick의 CPU/read/update 순서는 hook을 구현한 뒤 검증해야 하며, API를 찾았다는 사실을 구현 PASS로 표시하지 않는다.
- predictor exposure는 current logical hardware state이며 SW history-buffer slack, pointer, BranchInfo checkpoint metadata 및 architectural PC/data는 제외한다. O3의 in-flight history가 정상 squash로 복원되는 것은 허용하고 로그로 구분한다.
- 사건 RNG는 predictor RNG와 독립. fault가 CPU 실행을 늦추면 동일 work 종료까지 같은 외부 intensity 아래 사건 시계가 계속 진행해야 한다.
- native checksum mismatch, assertion, timeout, syscall failure를 masked fault로 세지 않는다. 첫 CPU 시험은 작은 checksum + zero/one/repeated fault smoke이며 대량 CPU campaign은 아니다.

## 실제 per-bit rate와 E4의 관계

**E4의 상대 면적·delay·operation energy에는 target per-bit SEU rate가 필수 조건이 아니다.** 같은 기능·storage 방식·PDK/library/PVT/clock/load/ports/activity를 매칭하면 상대 cost를 측정할 수 있다. RTL 정상 동작과 오류·repair 동작의 에너지를 분리한다.

실제 환경에서 평균 failure rate나 장기 평균 repair energy를 구하려면 노출 시간과 발생율이 필요하다. 아직 자료가 식별하지 못하는 target 값은 만들어내지 않는다. 우선 rate sweep과 동작당 cost를 보고하고, source-condition CHARM 관측율을 target의 측정율이라고 쓰지 않는다. 평균 bit-flip intensity를 외부에서 지정한다면 `lambda_event = mean_bit_flip_rate * B_exposed / E[K]`로 정의할 수 있으나 이는 susceptibility/geometry 가정과 함께 보고해야 한다.

## 진행 순서

E1의 관측창/분리 구간 검증과 S* 동결 → E2의 같은 세 보호법 → E3 주입·pipeline 검증과 E4 reference/RTL/PPA를 병행 → E4 실제 latency를 E3에 반영 → E5 통합. 현재 추가 dataset 업로드나 TCAD 요청은 없다.
