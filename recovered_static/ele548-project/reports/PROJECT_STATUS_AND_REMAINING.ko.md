> 2026-10-13 추가 연구 갱신: 기존 완료 기준선 이후 P_PERIODIC_ED(k32)를 구현해 CPP369oddbit/speculation 정확성, design84·source-pattern holdout96·실제O3 gate13·CPU42 pilot와matchedCI를 완료했다. 이번가정(C1/R4,update lane 추가지연0)에서 qsort는순이득7.2812pp, dijkstra는0.0745pp손해다. 상세결과·한계는 PERIODIC_EXTENSION_REPORT.ko.md와 PERIODIC_EXTENSION_AUDIT.json을 따른다. Adaptive/rebuild와실제RTL/PPA는미완료이며 기존4기준선·S*는유지한다.

# ELE548 소프트웨어 진행 상태와 남은 작업 — 2026-10-13

**Cadence 전 승인된 소프트웨어 연구 범위를 완료했다.** E0/E1/E2, Flying Laptop·CERN 모델 민감도, 실제 MiBench gem5 O3 main4092 및 assumed latency687, 분석·그림·최종 검토가 완료되었다. 모든 최신 실험은 RNG namespace v2다. 소프트웨어 정확성/성능 결과와 실제 RTL/PPA 완료를 구분한다.

## DONE — 실제 실행·검토 증거

| 단계 | 완료 결과 | 근거 |
|---|---|---|
| E0 | Gshare200k, plain TAGE upstream differential150k, logical injection/signed/raw/folded/snapshot/RNG/rollover | STAGE0_REPORT.md, original source/predictor manifests |
| E1 | 5760 design +600 warmup sensitivity; 6 HW1 traces, 동일 post100k conditional horizon와 disjoint holdout; S* raw_path+folded346 bits/23words | E1_REPORT.ko.md, protection_scope.lock.json |
| E2 | 같은 S*의 P0/P_ED/P_ECC/P_TMR, 실제 reset/relearn·SECDED writeback/DUE·vote/repair 및 추가 bit/보장 밖 오류; 8184 holdout trials | E2_REPORT.ko.md |
| Flying Laptop | 원본2129/2055/74 audit; 2880 detection-time-pattern trials | FLYING_TIMING_REPORT.ko.md |
| CERN | 3파일 MD5·전수 parser; 8640 conditional footprint trials; standalone2014/2015 및2020 원문 전체 검토 | CERN_METHOD_REVIEW.ko.md, CERN_FOOTPRINT_REPORT.ko.md |
| E3 정상 CPU·gate | MiBench qsort/dijkstra/SHA1 native 정답·pristine O3 baseline, 38 actual injection/speculation/timing gate cases | E3_PUBLIC_CLEAN_BASELINE.ko.md, E3_INTEGRATION_GATE.json |
| E3 CPU | pilot52 +main4092 +assumed-latency687 완료; 실패0; direct raw stats/config/event/answer/hash audit | E3_CPU_MAIN/LATENCY_SUMMARY.json, E3_CPU_REPORT.ko.md |
| 소프트웨어 통합·검토 | matched-seed bootstrap2000, scientific PNG/PDF, source/model/recovery/CPU 연결과 최종 검토 | SOFTWARE_INTEGRATION_REPORT.ko.md, SOFTWARE_FINAL_REVIEW.json, SOFTWARE_COMPLETION_AUDIT.json |
| E4 software 인계 | 기능·assumed timing·storage/exposure·operation-count proxy 계약, 모든 완료 CPU phase activity export | E4_SOFTWARE_FUNCTIONAL_HANDOFF.ko.md, E4_SOFTWARE_ACTIVITY_EXPORT.json |

Main wall time 약6.54h, latency 약1.10h, 각24workers였다. Runtime은 실험의 실행 비용이며 modeled CPU cycles와 다르다. 기존 namespace-v1 자료는 archive에 보존하고 최종 IID 신뢰구간 근거에서 제외했다. S* SHA-256 dec5020e5a504d0cdf49589e0acc4d2f7e8aa6c61798f61685b468d6dfdefe7b는 유지했다. Gem5 v25.1.0.1 commit c8222cc67a399bfc01e8658dd14b30d5bfd634f9와 기본 TAGE 알고리즘/update schedule도 유지했다.

## 결과의 의미

Ideal latency selected-payload CHARM6T/main stress에서 qsort의 P0 평균 cycle slowdown은10.3892%, P_ED는0.06872%, P_ECC는0.001495%, P_TMR는0%였다. 같은 latency-phase owners의 3개 program 평균에서는 P0 이상적 slowdown2.68059%에 비해 protected C1/R1 약4.25%, C4/R4 약47%였다. 가정한 검사 비용은 복구 이득보다 클 수 있다. 각program/조건·신뢰구간은 CPU 및 통합 보고서에 있다. 서로 다른 main/latency seeds의 평균을 직접 paired comparison으로 합치지 않는다.

## NOT DONE — 사용자 결정으로 유예한 실제 하드웨어 단계

1. 동일 기능·storage/interface와 PDK/library/PVT/clock/load를 고정한 RTL 구현 및 C++↔RTL operation/cycle 동등성.
2. 실제 ports/arbitration/throughput와 read/check/vote/correction/repair latency 검증.
3. Cadence의 실제 area/delay 및 switching 기반 power/energy 비교.
4. 실제 측정 C/R를 E3에 반영하고 hardware cost까지 포함한 E5 최종 보호 선택.

현재 승인된 소프트웨어 범위에 남은 필수 실험이나 사용자 준비는 없다. 새 SPEC 설치는 필요하지 않다. 이후 actual SPEC CPU application을 추가하려면 별도 배포본/권한이 필요하지만 현재 결과에는 요구하지 않는다.

## 검증한 가정·해석 한계

- HW1은 CBP/SPEC2006 유래 branch traces, 실제 CPU workload는 공개 MiBench ELF/input이다. 공식 SPEC CPU execution/score라고 표기하지 않는다.
- CHARM은 K 경험적 weights, CERN은 기록된 K≥2 군집 footprint, Flying Laptop은 detection-time pattern 근거다. Branch/cycle stress rate는 target bit⁻¹s⁻¹ 측정값이 아니다. Duplicate records를 MCU로 바꾸지 않는다.
- 제공받은 L11 p6은 singleton SBU와 K≥2 Type A를 구분한다. 논문 예시의 spatial/time thresholds는 현재 65nm raw files의 실제 생성 설정으로 확인되지 않았다. 해당 한계와 origin/singleton completeness/true-strike identity를 보존한다. 기존 input card는 historical frozen bytes, 새 source 해석은 cern_method_review_addendum_20261013.json을 따른다.
- 가상 footprint mapping은 physical layout/pitch 측정이 아니다. Targeted-payload TMR는 두 healthy copies가 있어 물리적 replica isolation을 증명하지 않는다. 별도 E2/E3 full-population에 추가 저장 bits 노출을 포함했다.
- CPU radiation exclusions와 C/R assumptions를 config/manifest에 명시했다. Activity counters는 VCD/SAIF/energy가 아니다. Statistical CI는 fixed programs/traces와 선언 모델 안의 seed 변동성이며 물리 flux/PDK 및 unseen workload 불확실성을 포함하지 않는다.
- Actual RTL/PPA, silicon 성능, mission FIT/TCAD/Geant4/TAGE-SC-L을 주장하지 않는다. TCAD는 사용 불가로 제외했고 Cadence는 아직 실행하지 않았다.

## 재현·다음 작업

각 source/config/binary/input/seed/schedule/raw log 및 summary hash를 보존했다. 재분석은 scripts/summarize_e3_cpu.py --phase main/latency, scripts/render_software_integration.py, scripts/audit_software_completion.py를 사용한다. 기존 campaign을 다시 실행할 필요는 없다. 실제 E4 재개 때 /home/youns/ASIC/sram_fft_top flow를 reference로 사용하고 동일 PDK/조건부터 고정한다.
