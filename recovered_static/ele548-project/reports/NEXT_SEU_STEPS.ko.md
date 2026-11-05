# 다음 소프트웨어 SEU 단계 — 2026-10-12

최신 실행 갱신: O3 logical SimTick/기본 세 보호법/speculative rollback/actual commit refill/response hold를 구현하고38-case gate+실제52-run pilot PASS. Ideal CPU main4092→latency687 runs가 실행 중이다. Flying Laptop detection-gap stress2880 trials와 CI/그림 완료. 최신 source/state는 `E3_INTEGRATION_REPORT.ko.md`, `E3_CPU_PILOT.json`, `E3_CPU_MAIN.json`, `FLYING_TIMING_REPORT.ko.md`를 우선한다. CERN full-method review/footprint는 원문 접근 제한으로 남는다. 완료되지 않은 CPU main/latency를 완료로 표시하지 않는다.

E1 design은 완료했다. 실제 HW1 trace 6개에서 M0 3600 + CHARM 2160 trials, 실패 0. 정확한 100k post-event horizon과 원 instruction denominator를 사용했고 warmup sensitivity 600 trials를 추가했다. `raw_path + folded` 346 bits/23 natural words를 `E1_SSTAR_V1`로 동결했다. Source/config/CI/한계는 `E1_REPORT.ko.md`, `E1_SUMMARY.json`, `sources/protection_scope.lock.json`에 있다.

E2/E3 갱신: 같은 S*의 P0/P_ED/P_ECC/P_TMR C++ 구현과 8184 holdout trials를 완료했다. 실행 실패 0. 추가 check/replica/controller bits도 실제 manifest에 포함했다. 공개 MiBench 3개 native 독립 정답 및 O3 clean baseline도 완료해 cycles/IPC/committed MPKI를 확보했다. `E2_REPORT.ko.md`, `E2_SUMMARY.json`, `E3_PUBLIC_CLEAN_BASELINE.ko.md`를 우선한다. CPU FI/보호 latency 비교는 미실행이다.

## 다음 작업

1. **E2 완료**: 같은 S*의 세 recovery 구현, clean twin equivalence, check/repair/refill 및 모든 added cells 검증. CPU epoch/rollback 처리는 E3 gate로 남는다.
2. **Holdout과 반복 영향 완료**: 분리한 HW1 input/seed, same base events와 added-storage exposure, SBU/CHARM equal-event/equal-expected-flip 비교. Physical footprint와 실제 repair delay sensitivity는 후속 단계다.
3. **Dataset 확장**: CERN grouping/sentinel/singleton 의미와 target logical footprint mapping 검토; Flying Laptop detection-time replay/time-shuffle를 명시한 stress로 연결. 실제 joint distribution/target bit-rate로 오해하지 않게 모델 카드 유지.
4. **E3**: gem5 O3 실제 application native/output validation·ROI·CPU baseline, SimTick event hooks/priority/speculation/squash/state handling, 같은 세 보호법의 clean/faulty cycles/IPC/MPKI. 현재 gem5는 checksum만 PASS이며 CPU FI/대표 성능 미실행이다.
5. **E4/E5는 이후**: PDK/library/PVT/clock/storage 결정·RTL/Cadence PPA는 사용자 결정으로 유예. 실제 check/repair latency는 측정 후 E3에 반영. TCAD 제외.

## 현재 사용자 조치

HW1 데이터 사용, 서버 제한 없음, software 성능 저하에 집중한다는 사용자 결정을 반영했다. 신규 SPEC 배포본/설치 또는 추가 radiation dataset 업로드는 현재 필요하지 않다. 사용한 long input은 SPEC2006 유래 trace이며 실제 SPEC program 실행이라고 표시하지 않는다.

## Cadence 참고

기존 `/home/youns/ASIC/sram_fft_top`의 C-shell `cadence-activate`와 별도 flow/library 설정을 이후 참고한다. 현재 tool activation/license checkout/PPA는 실행하지 않았고 기존 ASIC DB를 변경하지 않았다.
