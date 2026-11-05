# 소프트웨어 완료 증거 audit — 2026-10-13

**Cadence 전 소프트웨어 범위 완료, 최종 직접 검토 PASS.** scripts/audit_software_completion.py는 original hashes, frozen S*, raw C++ CSV와 사건 목록, original trace windows, CPU raw stats/config/event/output/hash를 대조한다. SOFTWARE_FINAL_REVIEW.json은 완료 통계·출처·과학 그림·한계의 직접 검토 기록과 evidence hashes를 남긴다.

| 요구사항 | 확인 증거 | 결과 |
|---|---|---|
| E0 | 원본 source18, unchanged upstream TAGE4files, frozen logical scope 및 correctness gates | PASS |
| E1 | corrected design5760, actual accounting/namespace·6개 original disjoint windows, warmup600, 기존 S* 보존 | PASS |
| E2 | same346bits/23words, corrected holdout8184, paired actual events·normalization·added exposure | PASS |
| Flying/CERN | 2129/2055/74, CERN3 MD5/full parse; corrected2880/8640 원시 결과·사건 hash | PASS |
| CERN 원문 | supplied standalone2014/2015/2020 전체 검토·PDF/text/figure hash, frozen input card 보존 | PASS; 파일별 threshold/target rate/layout은 미확인 |
| 실제 CPU | MiBench native/pristine, O3 gate38, pilot52/main4092/latency687 완료·native 정답·actual counters/config/events | PASS; 실패0 |
| 통계·그림·통합 | matched seed bootstrap2000, 3고정 programs weighting, full report/PNG/PDF 직접 검토 | PASS |
| E4 software 인계 | 기능·assumed timing·storage/exposure/활동 proxy 계약과 completed-phase export | PASS; 실제 RTL/PPA는 유예 |

Audit PASS는 silicon signoff, measured target per-bit rate, physical footprint 또는 actual Cadence 비용을 의미하지 않는다. 범위 밖/미확인 항목은 모델 카드·원문 addendum·config·인계 문서에 보존한다. 전부 정상 종료한 현재 CPU 실험에서도 failure 계약과 attempted 분모는 삭제하지 않았다. Namespace-v1 raw 자료와 씨드 오류 기록을 보존하고 최종 IID CI는 v2 결과로 제한했다.

남은 것은 이후 사용자 결정으로 재개할 실제 E4 및 hardware-cost E5다. 신규 SPEC/PDF 설치 요청이나 current software blocker는 없다.
