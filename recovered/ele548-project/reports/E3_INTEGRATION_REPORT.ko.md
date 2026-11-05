# E3 CPU 주입·복구·응답 경로 검증 — 2026-10-12

DONE: 분리된 pinned gem5 worktree에 logical-bit SimTick 주입, 같은 S*의 ED/ECC/TMR, speculative history generation/refill/drain, predictor response hold를 구현했다. Upstream `tage_base.hh/.cc`, `tage.hh/.cc`는 원본 hash와 동일하다. 새로운 wrapper와 최소 transport patch만 추가했다. 기존 baseline 소스/실행 결과를 보존했다.

## 검증한 동작

- 직접 upstream speculative schedule 대비 네 설계: 30k predictions, 10k young discard/older corrected rollbacks, 20k commits 각각 full-state/RNG equality. Small 4096-byte buffer rollover와 accelerated unit-test u-aging도 포함한다. 실제 CPU는 locked logUResetPeriod=18이다.
- ED/ECC DUE의 history reset 후 old generation restore/training을 억제한다. Bimodal training과 원래 aging은 계속한다. Speculative 입력은 refill에 세지 않고 actual committed controls 130개로 채운다. 이후 CPU BPU history queue가 비었을 때 tagged providers를 다시 허용한다.
- 실제 O3 checksum 38 cases: 네 설계 no-fault, raw/folded single, added check/replica/controller, even parity miss, SECDED DUE/triple miscorrection, correlated TMR cases, signed counter bit, same-tick cancellation, repeated events, repair 중 arrival, commit-origin repair.
- 같은 tick 사건은 queue priority49에서 file 순서대로 atomic unique-ID XOR 후 CPU tick priority50이 실행된다. 실제 logs에서 event→lookup 순서와 before/after XOR를 검증했다. Future unused schedule events는 정상 process exit에서 censoring으로 기록한다.
- 같은 checksum의 no-fault cycles/instructions/committed MPKI는 pristine optimized baseline과 일치한다. 네 설계의 canonical base-state hash와 predictor RNG draw count/hash도 일치한다. Shared upstream algorithm verification이며 독립 TAGE 재구현 검증으로 부르지 않는다.

## Software timing 가정

Decoded control instruction을 Fetch에서 hold하고 `check_due` 때 history check/read로 direction/BranchInfo를 얻는다. Cached response는 `response_due` 전에 전달하지 않고 squash 시 취소한다. Opcode를 다시 decode하거나 branch를 먼저 pipeline에 전달한 뒤 generic penalty만 추가하지 않는다. Event clock은 hold 중에도 진행한다.

Check latency C, repair hold R은 **가정한 cycle 값**이다. Storage writeback은 검출 시 시작하고 repair batch가 response port를 R cycles 점유한다. Backend update lane은 독립적으로 계속한다. Read/consume/speculative/commit/corrected/discard 어느 경로에서 검출돼도 response-port hold에 반영하고 busy 상태에서 새 repair batch는 직렬로 연장한다. Multiple-word repair는 한 parallel batch 가정이다. Consumption/history RMW integrity check의 clean 추가 cycles는 0으로 가정했다. 이 기능과 timing은 RTL 실측이 아니다.

이전 시험에서 backend 검출의 repair hold가 연결되지 않은 부분을 확인해 수정했다. 이전 32-case gate와 source를 `e3_integration/before_global_repair_hold`에 보존했다. 최종 38-case gate에서는 commit-origin repair가 실제 hold를 발생시키고 repair 중 새 오류가 4→8-cycle busy를 만든다. Pipeline overlap 때문에 전체 Δcycles는 hold 수와 항상 같지 않다.

## Storage exposure 경계

S* payload는 여전히 raw/path+folded 346 bits/23 words다. ED/ECC CPU controller에는 기존 8-bit refill와32-bit epoch에 **recovery_active 1 bit**를 추가했다. Total core+extras: P0 65370, ED 65434, ECC 65532, TMR 66062. 이 flag도 실제 주입 시험에 포함했다.

Existing CPU queues/checkpoints/BranchInfo, added in-flight epoch/fallback copies, pending decoded instruction/response, absolute simulator timing tags, BTB/RAS/architectural state, allocator/aging metadata와 shared combinational SET는 **명시적으로 radiation exposure 밖**이다. 이 결과를 full-CPU radiation qualification으로 표시하지 않는다. E4의 system-level cost에서는 필요한 transport/generation 구현을 따로 검토해야 하며 현재 counts를 전체 회로 PPA로 쓰지 않는다.

## Representative CPU pilot과 본실험

공식 MiBench qsort/dijkstra/SHA-1 static ELF/input을 같은 configuration으로 사용했다. 52-run pilot 전부 native 정답/exit 및 schedule accounting PASS. 실제 세 프로그램의 네 clean designs가 CPU counters, canonical base-state 및 RNG hash까지 같다. 두 프로그램의 single/repeating SBU/CHARM도 포함했다. Helpful/zero effects를 제거하지 않았다.

고정 main 계획은 ideal4092 +latency687=4779 runs다. Main CPU는 실행 중이며 완료 결과나 최종 보호 순위로 부르지 않는다. Rate1e-7/1e-6 events per CPU cycle은 software stress다. Model stop은 pristine duration의4배이며 느려진 설계는 동일 external clock에서 더 많은 arrival을 받는다. Model/wall timeout은 failure로 남긴다. Scope/input/seeds/normalizations/latency/runtime budget은 `configs/e3.cpu.lock.json`에서 확인한다.

## Evidence / NOT DONE

`sources/gem5_e3_source.lock.json`, `e3_integration/gem5_transport.patch`, `E3_INTEGRATION_GATE.json`, `E3_CPU_PILOT.json`, per-run config/stats/event/read/repair logs, source/binary hashes가 evidence다. `test_gem5_e3.py`, `run_e3_cpu.py`로 재현한다. E2 completed campaign의 exact old producer binaries는 source commit7ac23ab에서 재구성해 기존 hash와 동일함을 검증했다. 새 common-API regression binaries는 별도 보존했다.

NOT DONE: representative main/latency campaign 종료·CI·그래프·해석, CERN full-method grouping/footprint qualification, 실제 RTL latency/PPA. CPU 전체 checkpoint serialization은 구현하지 않아 매 run 전체 prefix를 재실행한다. Cadence/TCAD/Geant4/TAGE-SC-L을 실행하지 않았다.
