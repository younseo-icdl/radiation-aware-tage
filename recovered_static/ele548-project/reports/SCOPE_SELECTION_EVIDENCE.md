# S* 선정 전 근거 (Stage0; 아직 동결하지 않음)

후속 갱신: E1 design 5760 trials 이후 `raw_path + folded` 346 bits를 동결했다. 최신 근거는 `E1_SCOPE_SELECTION.ko.md`와 `sources/protection_scope.lock.json`이다. 아래 내용은 Stage0의 작은 pilot 당시 근거로 보존한다.

**IMPLEMENTED/TESTED RESULT:** 두 실제 course trace slice에서 240개 M0 SBU trial을 실행했습니다. 각 field에서 logical bit와 10k conditional-branch window의 주입 ordinal을 균등 표본화합니다. 20k conditional branches를 warm-up한 뒤 즉시 정답 update 방식으로 replay합니다. 원본 파일, 추출 record 범위와 hash는 `workload_windows.json`, 모든 사건 seed/site는 `pilot_240trials.csv`에 있습니다. workload 대표성이나 warm-up 안정성은 아직 입증하지 않았습니다.

| Workload | Field | 영향 trial / 20 | Harm | Help | Net |
|---|---|---:|---:|---:|---:|
| SHORT-INT-1 | bimodal | 0 | 0 | 0 | 0 |
| SHORT-INT-1 | ctr | 2 | 2 | 1 | 1 |
| SHORT-INT-1 | tag | 1 | 0 | 2 | -2 |
| SHORT-INT-1 | u | 0 | 0 | 0 | 0 |
| SHORT-INT-1 | raw/path | 19 | 404 | 151 | 253 |
| SHORT-INT-1 | folded | 20 | 858 | 401 | 457 |
| SHORT-FP-1 | bimodal | 0 | 0 | 0 | 0 |
| SHORT-FP-1 | ctr | 1 | 1 | 0 | 1 |
| SHORT-FP-1 | tag | 1 | 1 | 1 | 0 |
| SHORT-FP-1 | u | 0 | 0 | 0 | 0 |
| SHORT-FP-1 | raw/path | 19 | 2956 | 534 | 2422 |
| SHORT-FP-1 | folded | 20 | 691 | 178 | 513 |

Harm/Help는 각각 clean-correct/faulty-wrong 및 clean-wrong/faulty-correct의 conditional branch 개수입니다. 같은 사건의 후속 branch들을 독립 trial로 세지 않습니다. Zero-impact를 유지했으며 negative net도 남겼습니다. field당 사건 수가 동일하므로 이 표를 전체 predictor exposure로 pooling할 수 없습니다. Field bits는 bimodal 10,240 / ctr 10,752 / tag 36,864 / u 7,168 / raw-path 146 / folded 200이며, exposure-weighted 평가와 per-event 민감도를 별도로 제시해야 합니다.

**SOURCE FACT:** pinned `tage_base.hh`의 `FoldedHistory::update`는 이전 comp와 새/outgoing raw history bit를 사용합니다. `tage_base.cc::gindex/gtag`는 이 저장 comp를 조회합니다. Raw corruption 후 injector가 folded를 재계산하는 기능은 없습니다. raw와 folded는 독립 논리 상태입니다.

**DESIGN HYPOTHESIS:** raw/path 및 folded가 다음 E1의 우선 후보입니다. 작은 table 표본의 무영향은 table 보호가 불필요하다는 증거가 아닙니다. 미사용 row의 latent fault가 남을 수 있고, 본 replay는 speculative rollback/in-flight state를 제외합니다. Raw corruption이 정상적으로 밀려나더라도 derived state와 후속 allocation 차이가 남을 수 있습니다. 마지막 prediction divergence는 복구 시점이 아니며 종료 시 state 차이는 right-censored로 취급합니다.

다음 순서:
1. E0/O3 checksum은 통과했다. 이제 design 전용 workload/구간/seed를 설정합니다. 20k warm-up의 안정성과 긴 관측창을 먼저 확인합니다.
2. raw-direction vs path, index-fold vs tag-fold subfield를 나누어 active/latent와 영향 잔여를 측정합니다. Tagged field는 lookup frequency와 bit-weighted exposure도 함께 봅니다. Uniform exposure를 hottest-entry sampling으로 바꾸지 않습니다.
3. CHARM 6T/8T를 각각 유지한 MCU sensitivity를 추가합니다. CERN은 grouping/sentinel/singleton 의미 확인 후 별도 condition-specific footprint로 사용합니다. D01 시간 replay는 detector-stream 확장입니다.
4. design split에서 상위 1~2 module group과 codeword grouping을 S*로 동결합니다. 평가 workload 또는 구간/seed를 분리합니다.
5. 동일 S*에 P0/P_ED(parity+skip/relearn)/P_ECC(SECDED+writeback+DUE fallback)/P_TMR(vote+repair) 모두를 구현·비교합니다. 추가 보호 bits 및 control state를 manifest에 넣거나 제외 범위를 명시합니다.

TCAD는 사용하지 않습니다. 같은 PDK의 실제 구현 비용 및 latency는 E4에서 얻고 E3 timing에 반영합니다. 이 pilot은 최종 보호법 우승자나 PPA를 결정하지 않습니다.
