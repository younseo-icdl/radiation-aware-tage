# Cadence 전 소프트웨어 기능 인계 — E2

이 문서는 RTL 구현을 시작하거나 PPA 완료를 의미하지 않는다. 사용자 결정에 따라 Cadence를 유예한다. E3의 실제 CPU speculation/rollback과 latency contract는 아직 미검증이므로 최종 cycle interface는 동결하지 않았다.

E3 후속 갱신: `E3_INTEGRATION_REPORT.ko.md`의 generation/actual commit refill/queue-empty drain과 response hold를 실제 O3 gate에서 검증했다. ED/ECC에는 CPU recovery_active 1 bit가 추가돼 total ED65434/ECC65532다. In-flight epoch/fallback copies와 pending transport state는 명시적으로 radiation scope 밖이며 이후 system-level 구현 비용을 검토해야 한다. Software timing 가정은 check C completion→writeback begins→모든 origin repair batch의 serialized R response-port hold이며 backend update lane은 계속한다. RTL 실측 timing 및 전체 system PPA는 아직 없다. 아래 E2 기능/저장 표는 당시 atomic non-spec reference다.

## 구현·검증한 기능

S*는 `sources/protection_scope.lock.json`의 `E1_SSTAR_V1`: raw direction history 130, path 16, 21 folded registers 200 = 346 payload bits/23 natural words. Hardware bit는 logical ID로 지정하며 C++ byte/pointer/slack는 노출하지 않는다. 기본 plain TAGE의 table geometry, folded update, allocation RNG, usefulness aging은 upstream pin을 따른다.

- P0: 보호 없이 원래 TAGE lookup/update.
- P_ED: word마다 even parity 1 bit. Lookup 및 history read-modify-write 전에 검사. 어떤 S* word든 mismatch이면 의존된 전체 history scope를 reset하고 tagged providers 및 신규 tagged allocation을 제외한다. Bimodal training과 upstream usefulness aging은 계속한다. 130 actual control updates로 history를 refill한 뒤 tagged 후보를 다시 허용한다. Even-bit error는 검출 보장하지 않는다.
- P_ECC: word마다 systematic shortened extended Hamming SECDED. Payload는 원래 cell에, Hamming checks/overall parity는 sidecar에 저장한다. Single error의 실제 syndrome을 정정하고 payload/check를 writeback한다. DUE면 P_ED와 동일 reset/refill을 사용한다. 3-bit 이상은 실제 decoder law에 따라 missed/miscorrected outcome을 허용한다.
- P_TMR: 원본+두 추가 payload 사본. Bitwise majority 후 불일치 사본을 모두 repair한다. Legitimate history write는 세 사본 모두에 반영한다. 동일 bit의 두 사본 오류는 잘못된 majority로 feedback될 수 있다.

Detector/controller에는 injector event/K/site list 또는 gold state를 전달하지 않는다. Injector는 전체 event의 ID/unique/bounds를 먼저 검증한 뒤 atomic XOR만 한다. Check/re-encode/repair는 명시한 read/write 동작에서 수행한다. Mere read 또는 injection 시 재인코딩하여 오류를 숨기지 않는다.

## 실제 저장 노출과 비용 경계

| Scheme | Base core bits | Added code/replica bits | Added controller bits | Total exposed bits |
|---|---:|---:|---:|---:|
| P0 | 65370 | 0 | 0 | 65370 |
| P_ED | 65370 | 23 | 40 | 65433 |
| P_ECC | 65370 | 121 | 40 | 65531 |
| P_TMR | 65370 | 692 | 0 | 66062 |

ED/ECC controller는 refill_remaining 8 bits, history_epoch 32 bits다. Epoch는 현재 non-spec C++ replay에서 소비되지 않으며 CPU rollback generation 처리를 위한 저장이다. 이 32 bits도 실제 fault manifest에 포함했지만 지금 CPU 효과를 검증했다고 표시하지 않는다. Derived noSkip은 저장 사본으로 추가하지 않으며 refill 값에서 조합적으로 결정한다.

Statistics counters, software vectors/addresses, circular-buffer slack, in-flight BranchInfo/backups, alternate selector/aging metadata, BTB/RAS/architectural state, combinational SET는 현재 노출 경계 밖이다. CPU in-flight generation metadata가 추가되면 E3 manifest/비용 경계를 반드시 갱신해야 한다. 이 표는 physical flop/macro area나 cross section이 아니다.

`sources/e2_protection_logical_manifest.json`은 추가 cells 전체와 natural codeword/replica 관계를 담는다. Full population CSV는 `build/e2_manifest`가 생성하며 hash로 잠근다. Check bits뿐 아니라 controller bits 및 replicas의 주입도 correctness test에 포함했다.

## 타이밍·activity 인계의 한계

C++ E2에서 read/check/correction/writeback/reset은 zero-latency atomic operation이다. 이는 functional reference이며 throughput/cycle 모델이 아니다. 실제 RTL의 check/repair latency가 나오면 E3 predictor response/hold/repair 경로에 넣어야 한다. Generic misprediction penalty 또는 CPU clock만 바꿔 protection latency를 대신하지 않는다.

Trial CSV에는 payload word_reads/word_writes, sidecar_reads/sidecar_writes, encode_words, voted_words, repair/refill operation counts가 있다. 이는 logical operation proxy다. Actual RTL switching/VCD/clock tree/PDK energy가 아니며 power로 환산하지 않는다. Raw history는 software ring buffer로 저장하지만 RTL 물리 구현에서 동일 130-bit history/shift semantics를 보장해야 한다.

## Evidence와 다음 gate

`reports/e2_correctness.log`: 120k controls clean direction/full-state/RNG equality 네 설계, SECDED 1868 single/47648 double stored-bit cases, 346 payload singles와 모든 추가 cells, parity double miss, ECC triple/four failure, TMR same-bit two-copy failure, actual 130-control refill, snapshot/atomic validation.

`reports/E2_CAMPAIGN.json`: holdout 8184 trials, failure 0. Single SBU, Poisson 반복 SBU/CHARM, 동일 사건율/기대 flip 정규화, paired base 및 추가 storage 노출. Physical MCU mapping/absolute target rate를 증명하지 않는다.

다음 gate는 E3 CPU speculation/rollback/tick ordering과 실제 latency sensitivity다. 이후 동일 input/interface/PDK/library/PVT/clock/load/storage 조건에서 C++↔RTL operation/cycle equivalence, saboteur 제외 synthesis, 네 설계의 실제 PPA 및 measured switching을 비교한다. TCAD는 사용하지 않는다.
