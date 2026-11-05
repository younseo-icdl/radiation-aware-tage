# Cadence 전 기능·타이밍·activity 인계 — E2/E3

동일 S*의 P0/P_ED/P_ECC/P_TMR를 C++와 실제 gem5 O3에 구현했고 정상 동등성·주입·복구·speculation/rollback·response hold gate를 통과했다. 이 문서는 그 **구현된 소프트웨어 계약**을 넘긴다. 실제 RTL ports/arbitration/clock interface, RTL timing·PPA는 아직 확정하거나 측정하지 않았다. 사용자 결정대로 Cadence는 유예한다.

Machine-readable 계약은 sources/e4_software_interface_contract.json이다. Source/scope/manifest hashes, 23개 word의 실제 logical IDs, controller/sidecar/replica 저장, operation 순서와 timing 가정, activity counter 의미를 기록했다. scripts/export_e4_software_contract.py는 audit가 완료된 CPU phase만 export하며 실행 중인 main 결과를 최종 activity로 표시하지 않는다.

## 동결 범위와 실제 저장

S*=E1_SSTAR_V1: raw direction history130 +path16 +folded21 registers200 =346 payload bits/23 natural words. Core65,370 logical bits이며 C++ padding/pointer/circular-buffer slack는 저장 용량이나 주입 모집단으로 쓰지 않는다. Upstream plain TAGE의 geometry/update/allocation RNG/aging을 유지했다.

| Scheme | Core bits | Code/replica extras | E2 controller | E3 CPU controller | E2 total exposed | E3 total exposed |
|---|---:|---:|---:|---:|---:|---:|
| P0 | 65370 | 0 | 0 | 0 | 65370 | 65370 |
| P_ED | 65370 | 23 parity | 40 | 41 | 65433 | 65434 |
| P_ECC | 65370 | 121 checks | 40 | 41 | 65531 | 65532 |
| P_TMR | 65370 | 692 replica | 0 | 0 | 66062 | 66062 |

ED/ECC는 refill_remaining8 +history_epoch32를 저장한다. E3는 recovery_active1을 추가했고 이 bit도 fault manifest·실제 주입 gate에 포함했다. E2 non-spec replay에서 소비되지 않던 epoch는 E3의 오래된 history restore/training을 억제하는 generation으로 사용한다. 실제 codeword/추가 cell IDs는 E2 manifest와 E3 gate의 logical_manifest.json에 있다.

기존 BranchInfo/CPU queue/checkpoint/BTB/RAS/architectural state, 추가 in-flight epoch/fallback copies, pending instruction/response, absolute simulator timing tags, allocator/aging metadata/RNG/stats/shared SET는 **현재 radiation exposure 밖**이다. 향후 하드웨어에 필요한 transport/generation metadata의 실제 비용도 별도로 포함해야 한다. 이 숫자는 전체 CPU 회로 PPA나 area/cross-section ratio가 아니다.

## 구현한 operation 계약

- Lookup/read와 history RMW 전에 23개 selected word를 검사한다. Legitimate history write/reset 후에만 parity/check 또는 replicas를 갱신한다. Mere read나 injection 직후 re-encode해서 오류를 숨기지 않는다.
- P_ED는 even parity mismatch 때 의존된 전체 history를 reset하고 tagged providers/allocation을 제외한다. Bimodal training과 upstream aging은 계속한다. Even-number word 오류에는 검출 보장이 없다.
- P_ECC는 실제 shortened extended-Hamming syndrome으로 single error를 정정·writeback한다. Double error DUE는 동일 reset/refill fallback을 쓴다. >=3-bit corruption은 missed/miscorrected outcome이 가능하다.
- P_TMR는 bitwise majority와 feedback repair를 수행하고 legitimate writes는 세 사본에 반영한다. 동일 bit의 두 사본 오류는 wrong majority를 만들 수 있다.
- E3 reset 때 epoch를 증가시키고 recovery_active/refill130을 설정한다. Old-generation 또는 fallback BranchInfo의 restore/tagged training을 억제한다. Speculative controls는 refill에 세지 않는다. Actual committed controls130으로 history를 채우고 CPU BPU history queue가 비면 tagged providers를 다시 허용한다.
- Detector에는 injector event/K/site list 또는 golden model을 전달하지 않는다. Injector는 unique-ID/bounds 전체를 먼저 검사한 후 atomic XOR만 한다. Fault RNG와 predictor RNG는 분리한다.

## 실제 경로에서 검증한 timing 가정

Decoded control instruction을 Fetch에서 hold한다. C-cycle check completion 때 history/lookup을 읽어 cached response를 만들고, pending response는 ready 전 pipeline에 넘기지 않는다. Squash는 pending instruction/response를 취소한다. Generation/mode가 변하면 retry한다.

Correction/reset writeback은 검출 시 시작한다. 한 callback에서 검출한 여러 word는 한 parallel repair batch라는 가정이며, response port를 R cycles 점유한다. Busy 중 다음 batch는 직렬로 연장한다:

`busy_until=max(current_tick,busy_until)+R*500`

Read/consume/speculative/commit/corrected/discard 모두 repair hold에 반영한다. Backend update lane은 독립적으로 계속하며 consumption/history-RMW integrity check의 clean 추가 cycles는0으로 가정했다. Event clock도 hold 중 계속된다. Injection priority49는 CPU Tick50보다 앞서고, 같은 tick의 distinct events는 file 순서대로 모두 적용한다.

C=1/2/4, R=1/4는 **assumed cycles**이다. 실제 RTL latency는 없으며 repair count×R를 전체 CPU slowdown으로 바꾸지 않는다. Pipeline overlap 때문에 실제 ΔCPUcycles는 response-hold count와 다를 수 있다. Gate38에는 commit-origin repair와 repair 중 arrival의 busy 연장도 포함된다.

중요한 RTL 연계 한계: 여러 ordered callback이 하나의 gem5 Tick에 발생할 수 있다. 현재 atomic software operation을 그대로 한 operation/cycle 하드웨어라고 주장하지 않는다. RTL에서 필요한 read/write ports, simultaneous frontend/backend access, reset·refill·repair arbitration 및 throughput을 정하고 그 제약을 CPU 모델에 반영해야 cycle-equivalence와 비용을 주장할 수 있다. 현재 abstract operation 계약은 실제 RTL port interface를 대신하지 않는다.

## Activity export의 정확한 의미

reports/e3_cpu/E4_activity_pilot.csv는 audit를 통과한 실제52-run CPU pilot의 per-run count export다. 완료한 main/latency phase의 summary가 생기면 동일 exporter로 추가 CSV를 만든다. reports/E4_SOFTWARE_ACTIVITY_EXPORT.json에 campaign/audit/CSV hashes가 있다. Failed trials가 있으면 row와 status를 보존하고 activity 수치를 빈칸으로 남긴다.

- word_reads는 **보호 검사**의 payload reads다. P0의0은 일반 TAGE가 storage를 읽지 않았다는 뜻이 아니다. TMR check는 word당3개 read를 센다.
- word_writes는 legitimate update/reset/correction의 declared word slots다. TMR repair는 실제 일부 사본만 바뀌어도3개 write slots를 센다. 실제 bit toggles와 같지 않다.
- sidecar_reads/writes는 parity/ECC code 접근이고 word별 width가 다르다. encode_words는 계수된 update/reset encode proxy이며 초기화·전체 combinational activity를 포괄하지 않는다.
- detected/corrected/DUE는 word outcomes다. 한 cluster가 여러 word를 손상시키거나 여러 검사가 이루어지므로 injected events와 같지 않다. reset_refill은 check별 reset 횟수이고 DUE word count와 구분한다.
- response_hold/drain_hold/repair_batches/repairs_by_origin은 protocol의 동작·hold 기록이다. 전체 extra CPU cycles 또는 gate-toggle count를 대신하지 않는다.

따라서 이 CSV를 cell energy/power로 직접 환산하지 않는다. 실제 per-bit switching, RTL VCD/SAIF, clock tree 및 PDK energy는 아직 없다. Raw history의 software ring buffer는 RTL에서 동일130-bit shift semantics를 유지해야 하며 software 구현 메모리 크기를 합성 용량으로 쓰지 않는다.

## Evidence와 남은 gate

E2: e2_correctness.log의 네 설계120k clean controls/full-state/RNG, SECDED1868 singles/47648 doubles, 모든 added cells·보장 밖 오류·130-control refill/snapshot/atomic tests. E2_CAMPAIGN.json의 holdout8184 trials, failure0.

E3: E3_INTEGRATION_GATE.json의 actual O3 gate38, E3_CPU_PILOT.json 및 E3_CPU_PILOT_SUMMARY.json의52-run native/schedule/state/counter audit. Actual program main4092+latency687은 실행 중이며 완료/CI/PPA 결론으로 쓰지 않는다.

이후 E4: 동일 logical capacity/function/interface/library/PVT/clock/load/storage 조건과 explicit port/arbitration 계약 → clean/FI/speculation/rollback/refill C++↔RTL operation/cycle equivalence → saboteur/log/stat 제외 synthesis → 실제 switching/area/delay/energy. 측정 latency와 throughput을 E3에 반영한 뒤 실제 비용 결론을 통합한다. TCAD/Geant4/mission FIT/TAGE-SC-L은 실행하지 않는다.
