> 최신 통계 gate: additive role seeds가 인접 trial과 겹치는 문제를 확인했다. 기존 실행 data는 reports/superseded_rng_streams/v1에 보존했으며 IID bootstrap CI를 최종 근거로 사용하지 않는다. S*와 비교 조건은 유지하고 namespace v2로 재실행 중이다. 사용자 추가 조치 없음.

# E2 holdout 보호 비교 — 2026-10-12

실제 HW1 trace 6개의 분리된 holdout에서 8184 trials를 완료했다. Execution failure 0. 동결된 S*는 `E1_SSTAR_V1`, raw/path + folded history 346 bits/23 words다. CPU cycles·IPC는 이 결과에 포함되지 않으며 gem5 E3에서 별도 실행한다.

## 단일 SBU — 같은 payload bit/time의 네 설계 비교

| Field | Scheme | 평균 ΔMPKI (95% trial bootstrap CI) | 평균 net extra misses |
|---|---|---:|---:|
| raw/path | P0 | 1.01515 [0.743385, 1.3233] | 796.9 |
| raw/path | P_ED | 0.00846745 [0.00723164, 0.00967231] | 6.492 |
| raw/path | P_ECC | 0 [0, 0] | 0 |
| raw/path | P_TMR | 0 [0, 0] | 0 |
| folded | P0 | 0.389734 [0.347957, 0.432751] | 292.2 |
| folded | P_ED | 0.00980004 [0.00860485, 0.0111446] | 7.65 |
| folded | P_ECC | 0 [0, 0] | 0 |
| folded | P_TMR | 0 [0, 0] | 0 |

SECDED/TMR의 selected payload SBU 결과는 정상 정정의 검증이다. Added parity/check/controller/replica bit 노출은 별도 storage_scaled_full 결과에 포함했다. Parity는 검출 후 해당 history를 초기화하고 tagged provider를 제외해 130 actual control updates 동안 bimodal로 예측한다. SECDED DUE도 동일 fallback을 사용한다. Tagged counter/tag는 fallback 동안 학습·할당하지 않으며 원래 usefulness aging은 유지한다.

## 반복 주입과 한계

Poisson gap에 CHARM 6T(205:9), 8T(142:5) K=1/2 분포를 각각 mark했다. 같은 사건율과 같은 기대 flip 수를 별도로 비교했다. 시간 단위는 conditional-branch exposure이며 1e-4/1e-3은 소프트웨어 stress rate다. 실제 target per-bit/second SEU rate로 보고하지 않는다.

selected_payload는 S*의 조건부 민감도, paired_base_full은 같은 전체 core 사건, storage_scaled_full은 추가 보호 저장 bit까지 같은 per-bit density에 노출하는 비교다. Added storage를 포함하면 설계마다 bit 수와 event count/site가 달라지므로 동일 사건으로 설명하지 않는다. 현재 MCU anchor는 logical sensitivity이며 실측 predictor geometry가 아니다.

보호기에는 injector event/K 또는 golden prediction/state를 제공하지 않았다. 모든 event가 atomic unique bits이며 모든 같은-bin 사건을 순서대로 적용한다. 한 trial 시작 때만 warmup으로 reset하고 반복 사건 사이에는 reset하지 않는다. Harm/help/zero는 모두 보존했다. Net>0는 predictor loss outcome이지 architectural failure/SDC가 아니다.

Decoder 이상의 오류도 실제 law로 처리한다: parity의 even-error miss, SECDED의 3-bit miscorrection/4-bit undetected case, TMR의 같은 bit 두 사본 majority failure가 correctness test에서 확인됐다. 인공적으로 성공 처리하지 않았다.

95% CI는 고정된 6개 workload 내 matched trial/seed bootstrap 2000회다. Branch를 독립 trial로 간주하지 않으며 새로운 프로그램 모집단/mission rate에 대한 CI가 아니다. Full-state endpoint equality와 last divergence는 영구 회복 보장이 아니다.

## 재현과 남은 작업

`bash setup/build_e2.sh`, `.venv/bin/python scripts/run_e2.py --phase preflight`, `--phase main`, `.venv/bin/python scripts/summarize_e2.py`. 입력/source/config/binary/manifest와 trial/event CSV의 hash는 `E2_PREFLIGHT.json`, `E2_CAMPAIGN.json`, `E2_SUMMARY.json`에 있다. 최초 compile failure는 vector<bool> proxy auto deduction 문제였으며 `e2/build_attempt1.log`에 보존하고 bool 명시로 수정했다.

DONE: 세 recovery behavior, clean equivalence, added-bit enumeration/injection, fixed holdout SBU/CHARM single/repeat 비교. NOT DONE: CERN physical grouping/footprint qualification, Flying Laptop time stress 연결, gem5 CPU FI·speculation/rollback·latency sensitivity, 실제 RTL latency/PPA. Cadence와 TCAD는 실행하지 않았다.
