> 추가방법pilot 완료: PERIODIC_EXTENSION_REPORT.ko.md 참조. 현재필수사용자조치는없다. 실제update-lane 지연/ports·PPA 측정, 더넓은rate/k grid·tail확인은후속범위다. Cadence보류·TCAD제외결정은유지한다.

# 사용자 조치 — 2026-10-13

**현재 승인된 Cadence 전 소프트웨어 범위에 필수 사용자 조치는 없다.** E1/E2·Flying/CERN 모델 시험과 actual MiBench O3 pilot52/main4092/latency687·raw audit·통계·그림·최종 검토를 완료했다. 신규 SPEC 설치, dataset/network/sudo/package/license 변경을 요청하지 않는다.

## CERN 원문 요청 해결

사용자가 제공한 2014/2015 standalone 논문과 REDW2020 PDF를 확보하고 전체를 검토했다. 추가 PDF 경로 요청은 해소되었다. 출처·hash·페이지는 sources/cern_methods.lock.json, 검토와 현재 한계는 CERN_METHOD_REVIEW.ko.md 및 data/curated/cern_method_review_addendum_20261013.json에 기록했다.

원문만으로 세 raw files의 실제 clustering code/threshold·singleton completeness·origin 의미·true-strike identity·target physical rate/layout까지 확인되지는 않는다. 현재 연구는 recorded K≥2 조건부 가설로 이를 명시했고, 이 metadata를 software 완료의 prerequisite로 만들지 않는다.

## 이후 실제 E4 재개 때 필요한 결정

- 공통 PDK/library/PVT/목표 clock/load/storage/interface·측정 범위를 고정한다. /home/youns/ASIC/sram_fft_top flow는 reference다. 현재 Cadence/TCAD를 실행하지 않는다.
- 실제 SPEC CPU application을 추가하는 별도 확장은 entitlement/배포본이 필요하다. HW1 CBP/SPEC2006 유래 traces 및 공개 MiBench 범위는 이미 완료했다.
- 선택적인 ASan 보완은 runtime 부재로 이전 두 시도에서 링크하지 못했다. Valgrind lifecycle0errors/0leaks 결과를 보존했다. 이 선택 보완을 위해 지금 system package/admin 조치를 요구하지 않는다.

최신 상태는 PROJECT_STATUS_AND_REMAINING.ko.md, SOFTWARE_INTEGRATION_REPORT.ko.md, SOFTWARE_COMPLETION_AUDIT.json이다. 과거 요청/실패 기록은 reports/inherited 및 superseded_rng_streams/v1에 보존했다. Namespace v2 전체 고정 예산과 검증을 완료했으며 v1 IID CI는 최종 근거에서 제외했다.
