# 반복 SEU 주입 구현·검증 — 2026-10-12

## DONE

`src/fault/event_stream.hpp`와 `src/replay/repeated.cpp`를 추가했다. predictor는 trial 시작 시 warmup snapshot을 **한 번만** 복원하고 10k conditional branches 동안 연속 실행한다. 사건마다 초기화하거나 gold 값으로 repair하지 않는다. 원본 TAGE 알고리즘 및 update schedule은 변경하지 않았다.

모델은 `N(T) ~ Poisson(lambda*T)`, gap은 `Exponential(lambda)`이며 K는 M0=1 또는 CHARM 6T(205:9)/8T(142:5)의 별도 categorical 분포다. `lambda`의 단위는 exposed predictor 전체에 대한 **events/conditional branch**, `lambda*E[K]`는 **flip operations/conditional branch**다. target events/second 또는 SEU/bit/second로 보정한 값이 아니다.

시간·K·field·anchor RNG는 predictor RNG와 분리했다. field는 B_j/65,370으로 선택하고 해당 field의 valid 연속 K-bit anchor를 균등 선택한다. SBU는 전체 exposed bit 중 균등이며 K2의 field endpoint 편향은 계약에 기록했다. logical adjacency는 물리 adjacency 측정이 아니다. SW pointer/padding/history slack 및 추가 보호 bits는 current P0 population에 포함하지 않는다.

branch coordinate [o,o+1)의 모든 사건은 조건분기 o의 prediction 전에 도착순으로 적용한다. K bits는 사건 내 atomic XOR이며 같은 bin의 여러 사건도 버리지 않는다. 서로 다른 사건이 같은 bit를 다시 맞히면 두 번째 XOR로 상쇄할 수 있다. branch 사이 물리 idle 시간이나 사건 중간의 recovery 동작을 모델링한 것은 아니다.

## IMPLEMENTED / TESTED RESULT

- 사전 고정된 `configs/repeated_pilot.lock.json`: 2 actual course trace windows × 3 profiles × 4 rates × 4 repetitions = **96 runs**. rate = 0, 1e-5, 1e-4, 1e-3; run당 기대 사건 수 = 0, 0.1, 1, 10. 이는 zero/sparse/repeating 동작 검사 예산이며 physical environment 또는 recovery 시간에 맞춘 main rate grid가 아니다.
- 실패 0, 총 사건 258, 총 bit XOR operations 268. 전체 약 3.03초, 최대 RSS 19,004 KiB. 같은 schedule을 profile마다 실행한 횟수를 포함한 합계이므로 258개의 독립 실측 사건이라는 뜻은 아니다.
- 모든 zero-rate run에서 gold와 전체 predictor state/RNG 동일. 0건이 우연히 발생한 nonzero-rate run도 같은 equality gate를 통과했다. 같은 event rate/seed에서는 세 profile의 도착 시각 일치.
- 추가 한 run의 schedule 및 모든 impact count가 원 실행과 정확히 일치. wall time/RSS만 비교에서 제외. 총 predictor 실행 97회로 첫 100-run 이내 budget 유지.
- 확률 generator 자체 20,000개 저비용 schedule 표본에서 목표 lambda*T=5에 대해 count mean=5.02135, variance=4.98939; N=1 조건의 normalized event-time mean=0.505597. 이는 sampling algorithm 시험이며 irradiation 측정값이 아니다.
- bit-weighted field 노출 및 CHARM categorical 빈도, 같은 branch bin의 복수 사건, 별도 사건의 동일-bit 재주입, continuous state, atomic MCU 검사 통과.
- 제공 Python 18 tests PASS. CERN 세 원본 파일 MD5 및 전수 parser 재검증 PASS. 자료 상태: `DATASET_READINESS.json`.

원 run별 harm/help/net, end differing logical bits, event/flip 수, seeds, 수행 시각/위치는 `reports/repeated_pilot/runs.csv`와 개별 `.events.csv`에 보존했다. 일부 run에서 helpful faults도 그대로 기록했다.

## ASSUMPTIONS / LIMITS

시간 과정의 homogeneous Poisson은 baseline 가정이고 CHARM에서 검증한 stationary target time law가 아니다. CHARM은 K만 source-informed이다. 시간과 K/location의 독립, 균일 cell susceptibility, field 내 logical pair는 가정이다. source-condition p(K2) 추정 불확실성과 K>=3 미관측의 한계는 이전 model card와 같다.

현재 동일 event-rate 비교만 실행했다. 동일 expected flipped-bit-rate 비교는 lambda = desired_flip_rate/E[K]로 별도 실행해야 하며, 결과를 이미 완료했다고 표시하지 않는다. 물리 bit별 susceptibility를 의미하는 scalar per-bit rate와 K2 endpoint 편향은 동일 개념이 아니다.

각 workload/model/rate에 4개의 독립 seed run만 있다. 서로 다른 profile/rate에서 공통 seed를 쓰므로 paired 비교이며 이들을 독립 표본으로 pool하지 않는다. 기존 Stage0 input 구간을 사용한 engineering pilot으로 **S* 선정·정책 우승·신뢰구간 결론은 없다**. Table bits가 노출의 대부분이라 raw/folded를 강제로 맞힌 진단과 영향 빈도가 다를 수 있다. 0-impact run을 삭제하거나 결과가 잘 나오도록 rate를 조정하지 않는다.

interacting events에서 특정 사건의 회복시간을 last prediction divergence로 정의하지 않는다. 관측끝 residual과 endpoint censoring을 유지한다. Stage0 single-event 관측의 late injection 문제는 equal-followup E1로 해결할 예정이고 이번 반복 pilot만으로 해결됐다고 주장하지 않는다.

## NOT DONE / NEXT

E1 equal-followup/warmup 안정성 및 disjoint input split, S* 동결, E2 TAGE 세 보호법, gem5 SimTick FI/speculation/checkpoint validation, E4 RTL equivalence/Cadence PPA, E5. 단계별 조건은 `E3_E4_READINESS.ko.md`에 기록했다. 현재 사용자 조치나 추가 dataset 업로드는 필요하지 않다.

## 재현

```bash
bash setup/run_repeated_pilot.sh
.venv/bin/python scripts/check_repeated_regression.py
.venv/bin/python scripts/qualify_current_datasets.py
.venv/bin/python -m unittest discover -s tests -v
```
