> 최신 통계 gate: additive role seeds가 인접 trial과 겹치는 문제를 확인했다. 기존 실행 data는 reports/superseded_rng_streams/v1에 보존했으며 IID bootstrap CI를 최종 근거로 사용하지 않는다. S*와 비교 조건은 유지하고 namespace v2로 재실행 중이다. 사용자 추가 조치 없음.

# E1 소프트웨어 오류 영향·보호 범위 선정 — 2026-10-12

## DONE

고정 plain TAGE와 HW1의 실제 6개 trace에서 **M0 SBU 3600 trials + CHARM 6T/8T 각 1080 trials = 5760 trials**를 실행했다. 전부 PASS, failure 0이다. 추가 72 preflight trials 및 SHORT-INT-1 warmup sensitivity 600 trials도 통과했다. Main wall time 30.77 s, 최대 process RSS 288916 KiB이며 이는 host computing cost다.

선정용 입력은 SHORT-INT-1, SHORT-FP-1, SHORT-MM-1, SHORT-SERV-1, LONG-SPEC2K6-00/01이다. Long 입력은 HW1에 배포된 SPEC2006 유래 CBP trace이며 실제 SPEC application binary를 실행한 결과는 아니다. 원 archive hash를 재확인했고 bounded record prefix의 PC/target/opType/taken 및 원 instruction index를 검증했다. 원본 HW1와 pinned gem5 source는 수정하지 않았다.

본실험 전 `configs/e1.design.lock.json`에 입력·주입·표본수·선정 rule을 고정했다. 모든 사건은 주입 직후부터 **100000 conditional branches**를 관측한다. Injection time은 20000-branch prefix 내 균등이며 snapshot은 1000-branch stride로 저장 후 정확한 주입점까지 정상 재생한다. Time/K/location RNG는 predictor RNG와 독립이다. Inactive rows, zero effects와 helpful faults를 유지한다.

각 trial의 ΔMPKI는 해당 주입 conditional instruction부터 H번째 conditional instruction까지의 **원 CBP instruction record 범위**로 계산했다. Branch-only CSV를 instruction 수인 것처럼 사용하지 않았다. 130/1k/10k/50k/100k 후의 누적 harm/help/net, exposed-state/control difference와 주소조회 진단을 기록했다.

## 정확성 gate와 실행 비용

- Observer가 추가된 adapter로 Gshare 200k/TAGE 150k source differential, full state/RNG/aging/snapshot/signed/raw-folded/rollover 검증을 다시 통과했다.
- 신규 C++ correctness: 동일 post-event 길이, 원 instruction 범위의 inclusive denominator, incomplete window 거부, read-only observer가 prediction/state/RNG를 바꾸지 않음을 확인했다.
- Python 20 tests: 기존 18개에 binary format/actual disjoint windows 및 late injection full horizon checks 2개 추가, 모두 PASS. Scope freeze 이후 same-scope 검사도 통과해야 최종 manifest를 채택한다.
- ZERO 6 trials의 모든 checkpoint에서 정상 exposed/control/RNG equality. Speed 60 trials: 평균 trial 0.01833 s, task wall 1.37 s, peak RSS 109284 KiB. Main 전에 projection과 예산을 기록했다.
- Repeat 6 trials의 모든 schedule/impact count가 speed run의 대응 trial과 정확히 일치; wall/RSS만 비교에서 제외했다.
- Worker 4개는 사용자 서버 제한 없음에 따른 고정 선택이며 64 CPUs 전체를 사용한 것이 아니다. Failures를 masked로 집계하지 않았다.

## S*와 효과

미리 고정한 **bit 노출 가중 signed ΔMPKI**로 상위 두 field를 선택했다. Uniform per-bit susceptibility는 가정이며 physical SRAM/FF rate를 측정한 것이 아니다. Statistical unit은 event trial이고 six fixed workload별 stratified bootstrap 2000회다. Source K uncertainty는 별도로 보고한다.

| M0 field | Mean net extra misses / 100k conditional branches | Mean paired ΔMPKI | Bits |
|---|---:|---:|---:|
| raw/path | 810.64 [713.53, 913.53] | 1.0251 | 146 |
| folded | 274.43 [261.21, 288.22] | 0.35602 | 200 |

괄호는 mean net의 95% trial-bootstrap interval이다. Field별 같은 600 trials이지만 전체 exposure가 같다는 뜻은 아니다. 가중 contribution과 나머지 table fields, source sensitivity는 `E1_SUMMARY.json`/`E1_SCOPE_SELECTION.ko.md`에 있다.

**동결된 S* = raw_path + folded, 346 payload bits / 23 natural words.** 이후 같은 범위·word 경계에 P0/P_ED/P_ECC/P_TMR를 모두 비교한다. 각 field의 natural raw/path/fold register를 word로 유지했다. Parity 23 bits, SECDED check bits 121, TMR extra replica bits 692는 codec storage 장부 계산이며 controller metadata·실제 구현·PPA 결과가 아니다.

Subfield 진단은 차이를 보여준다. Sampled raw-direction 538 trials의 평균 net은 약 904, path 62 trials은 약 0.39다. Folded index/tag folds는 각각 약 273–276이다. 이는 조건부 exploratory subfield 평균이며 workload별 subfield 표본수가 같거나 path가 항상 안전하다는 뜻은 아니다. 사전 field-level rule을 유지해 path도 raw_path scope 안에 남겼다.

원 raw history upset이 shift 밖으로 나간 뒤에도 derived folds와 뒤따른 allocation/learning 차이가 남을 수 있다. 실제 평균 cumulative net은 raw/path에서 130 branches 후 0.81 → 10k 후 68.95 → 100k 후 810.64로 증가했다. 이는 후속 영향의 관측이며 original physical bit가 100k 동안 고장 상태였다는 뜻은 아니다.

## Warmup·통계 한계

같은 ROI에서 20k/100k/200k/400k/500k warmup을 비교했다. 예를 들어 SHORT-INT-1의 clean MPKI는 3.0387 → 0.9883 → 0.8404 → 0.6569 → 0.5432였다. 따라서 Stage0 20k 결과를 곧바로 main ranking으로 쓰지 않았다. 사전에 정한 fallback으로 모든 workload에 full available 500k prefix를 사용했다.

SHORT-INT-1은 400k/500k clean metric에도 민감하다. 해당 trace의 동일 M0 events를 400k에서 추가 600회 평가한 sensitivity에서도 global top2는 raw/path와 folded로 같았다. **Warmup state가 stationary로 수렴했다고 주장하지 않는다.** 범위 선택은 이 finite-trace design 조건에 한정한다.

Bootstrap 2000회에서 두 field가 모두 top2였지만 이는 fixed trace/assumed exposure 아래의 empirical ranking stability다. 다른 application/CPU/speculative schedule/physical geometry 또는 보호 비용까지 포함한 보편적인 최적 보호법의 증거가 아니다. 최종 평가는 분리한 holdout input/seed에서 시행한다. Holdout file은 준비·구조 검증만 했고 prediction/performance는 평가하지 않았다.

Last divergence와 checkpoint의 observed semantic equality를 true recovery time으로 부르지 않는다. 100k 뒤에도 차이가 남은 사건은 endpoint-censored로 남긴다. Queried-address 진단은 tag-table 주소가 조회됐다는 뜻이며 ctr/u payload가 그 cycle에 functional decision에 쓰였다는 보장은 아니다.

CHARM profile별 30 events/field/workload는 K2 효과의 작은 sensitivity이다. 첫 30 M0 events와 같은 시점으로 paired 비교했고 K-dependent valid-anchor mapping을 기록했다. Source summary에는 K>=3가 미관측이며 불가능이라는 뜻이 아니다. CERN grouping과 Flying Laptop timing integration은 아직 별도 미완료다.

## NOT DONE / NEXT

E2의 실제 parity+exclude/relearn, SECDED+writeback/DUE fallback, TMR+repair controller와 추가 storage exposure, holdout 보호 평가가 다음이다. CPU cycles/IPC는 **gem5 O3의 별도 E3 application 실행·SimTick injection·speculation/rollback·latency 실험**에서 측정한다. 현재 gem5는 checksum 정상 실행만 통과했고 CPU FI/대표 performance는 미실행이다. Cadence/PDK/RTL PPA는 사용자 결정으로 유예한다. TCAD는 제외한다.

## 재현

```bash
.venv/bin/python scripts/prepare_e1_windows.py
bash setup/build_e1.sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/run_e1.py --phase preflight
.venv/bin/python scripts/run_e1.py --phase main
# flagged warmup sensitivity uses configs/e1.warmup_sensitivity.lock.json;
# run the dedicated script below before inference.
.venv/bin/python scripts/run_e1_warmup_sensitivity.py
.venv/bin/python scripts/summarize_e1.py
.venv/bin/python scripts/qualify_logical_manifests.py
```

Source/config/CSV/executable hashes는 `sources/manifest.json`, `reports/software.lock.json`, `E1_WORKLOAD_WINDOWS.json`, `E1_PREFLIGHT.json`, `E1_CAMPAIGN.json`, `E1_SUMMARY.json`에 보존한다.
