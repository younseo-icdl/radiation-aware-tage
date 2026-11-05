# CERN 군집 원문 검토와 사용 범위 — 2026-10-13

사용자가 제공한 standalone 2014/2015 논문과 REDW 2020 accepted manuscript를 sources/papers에 복사하고 SHA-256·버전·검토 페이지를 sources/cern_methods.lock.json에 기록했다. 세 원문 전체를 읽고 L10 p3 Fig3/TableII, L11 p2 Fig1–2 및 p6 TableI, L12 p6 Fig4–9 이미지를 확인했다. 공개 원문 취득 시도는 더 필요하지 않다. 첨부 문서는 연구 근거로 읽었으며 사용자 지시로 취급하지 않았다.

기존 캠페인에 hash로 결합된 data/curated/cern_footprint_model_card.json은 실행 당시 입력으로 보존한다. **현재 원문 가용성·singleton 분류 설명은 별도 cern_method_review_addendum_20261013.json이 우선한다.** Qualifier 재실행은 기존 card/확장 source lock을 덮어쓰지 않는다. 모델·입력·일정·S*·시드는 변경하지 않았다.

## SOURCE FACT — 원문에서 확인한 내용

| Source | 원문·PDF 페이지 | 확인 내용 |
|---|---|---|
| L10 | Multiple Cell Upset Classification in Commercial SRAMs, DOI 10.1109/TNS.2014.2313742, p1–8 | 90nm SRAM neutron static/dynamic 시험. Type A/B/C/D의 원인·패턴을 구분한다. MCU가 같은 logical word의 여러 bits를 손상시키면 MBU가 된다. |
| L11 | Investigation on MCU Clustering Methodologies for Cross-Section Estimation of RAMs, DOI 10.1109/TNS.2015.2496874, p1–7 | 공간·시간 proximity를 이용한 후처리. Logical-access Type C를 먼저 분리하고 나머지 physical patterns를 분류한다. |
| L12 | SEU characterization of commercial and custom-designed SRAMs based on 90 nm technology and below, DOI 10.1109/REDW51883.2020.9325822, p1–9 | CY62167GE30-45ZXI 65nm/16Mbit/datecode1731, FPGA firmware를 통한 내부 ECC disable, room-temperature 시험과 조건별 cross-section을 설명한다. |

L12는 기존 L08과 같은 논문의 다른 PDF 저장본이다. 표지 추출 텍스트에는 차이가 있지만 PDF p2–9 본문 추출 텍스트는 동일하다. 독립적인 두 실험 근거로 중복 계산하지 않는다. L09 Bosser thesis는 보조 근거로 보존한다.

**Singleton 분류 정정:** L11 PDF p6(printed p2625)는 K=1인 SBU와 남은 K≥2 Type A를 별도로 정의한다. 기존 thesis 요약의 “Type A에 singleton 포함” 표현을 이 논문의 분류 정의로 사용하지 않는다. 이 정정은 이미 K≥2만 사용하는 footprint 캠페인의 표본이나 결과를 바꾸지 않는다. 원본 singleton과 origin-flagged records도 계속 보존한다.

L10 p2–4와 L11 p2/Fig1–2는 logical address adjacency와 physical cell adjacency가 다름을 보여 준다. Address scrambling 및 bit interleaving 정보가 있어야 physical bitmap을 복원할 수 있다. L10 p6–8은 Type C/D의 일부 관측이 read/write/peripheral circuitry의 실패에서 생길 가능성을 논의한다. 특히 실패한 read가 곧 storage-cell flip을 증명하지는 않는다. 현재 K≤12 catalog의 각 record를 이런 기전으로 분류할 metadata는 없으며, 이 소프트웨어 시험은 SEFI/peripheral transient 모델까지 검증한 결과가 아니다.

## SOURCE FACT — 임계값과 grouping의 한계

L11 p3의 과거 iterative 방법은 각 upset 주변 3-cell proximity와 2-second detection 기준으로 오류를 확장·병합한다. 개선 방법은 p4에서 logical Type C를 먼저 제거하고, p5–6의 사례에서 horizontal10/vertical67 cells와 2 seconds를 사용한다. 이 값은 논문 시험 장치의 경험적 설정이다. L11 대상은 CY62177EV30LL-55ZXI이고 현재 데이터의 65nm CY62167GE30-45ZXI와 다르다.

L11 p6 TableI는 동일 데이터에서도 window/time 설정이 SBU·Type A/B/D의 집계를 바꿈을 보여 준다. p6–7은 높은 fluence/upset rate나 느린 memory refresh가 서로 다른 사건의 누적·군집 결합을 일으켜 분류 정확도를 떨어뜨릴 수 있다고 설명한다. 따라서 provider cluster는 후처리의 관측 단위이며 독립 particle strike identity가 자동으로 입증된 것은 아니다. **Clustering의 2 seconds는 CPU injection의 평균 사건 간격이 아니다.**

L11 p6 case-study 숫자에는 내부 불일치가 있다. 본문 총계204, 본문 세부28+137+29+5+3=202, event-cross-section 식의 분자176이 일치하지 않는다. TableI chosen row29+137+30+3에 Type C5를 더하면204가 된다. 어느 것이 정정값인지는 추정하지 않았고 이 사례의 수를 rate calibration에 사용하지 않았다.

이 원문으로 확인한 것은 방법과 한계다. 세 2023 raw 파일 각각을 만든 코드/실제 threshold, singleton completeness, ID0 origin 의미, live exposure·fluence 및 numerator convention, 실제 source coordinate pitch/scrambling과 target mapping은 여전히 식별되지 않았다. 논문 예시 parameter를 데이터 파일의 실제 생성 설정이라고 표시하지 않는다.

## DESIGN HYPOTHESIS — 기존 모델을 유지하는 이유

공급자 Zenodo 8314389는 proton/heavy-ion MCU 자료와 위 방법 논문을 연결한다. 세 파일 MD5 및 전수 문법 검증을 완료했다. 모집단은 파일별 **기록된 K≥2 군집**으로 고정하고 군집을 균등 복원추출한다. K는 unique coordinates 수다. Proton 29MeV는18개 K2 records, proton0.9MeV는52개 K2 records, Ar1050MeV는449개 K2–12 records다. 각 record의 K와 offsets 전체를 한 atomic software event에 유지한다.

S*346 bits를 16×22 logical tile에 두고 빈 cell6개를 남긴다. Word-contiguous, round-robin word-interleaved, dispersed same-K를 비교한다. 전체 shape가 들어가는 translation만 허용하고 clip/wrap/rotation하지 않는다. 실제 target pitch/배치가 없는 **조건부 logical mapping 가설**이다. 추가 보호 cells는 이 targeted 시험에서 제외하고 별도 E2/E3 full-population 조건에서 노출한다. Replica0-only TMR 결과로 실제 사본 간 공간 독립성을 주장하지 않는다.

반복 도착은 conditional-branch 좌표의 independent Poisson을 stress 가정으로 사용한다. Equal-event λ와 equal-expected-flip λ/E[K]를 분리한다. CERN의 관측된 군집 크기·offsets를 사용하는 것과 target particle arrival clock을 측정하는 것은 다른 일이다. 기존8640 trials는 이 선언한 모델을 이미 실행했으므로 원문 제공만을 이유로 동일 실험을 다시 돌릴 필요는 없다.

## NEW DERIVATION — rate의 의미

Source의 bit-flip cross-section σ_flip(E) [cm²/bit]와 해당 환경의 spectrum Φ(E) [particles/cm²/s/energy]가 알려졌다면 source per-bit expected flip rate는 ρ_flip=∫Φ(E)σ_flip(E)dE다. 적절한 event/population 모델 아래 expected flip rate는 event rate×E[K]로 구분한다. 군집 사건 cross-section과 bit-flip cross-section을 섞으면 multiplicity를 두 번 계산할 수 있다.

L12가 제공하는 source-device cross-section만으로 다른 storage/process/voltage의 TAGE target σ를 얻지는 못한다. 현재 stress λ는 branch/cycle 단위로 명시하며 physical bit⁻¹s⁻¹나 mission FIT로 환산하지 않는다. L12 Fig7의 Weibull LET response도 **단면적의 LET 의존성**이며 K의 확률분포 또는 arrival-time 분포가 아니다.

## IMPLEMENTED/TESTED RESULT · NOT DONE · NEXT

MD5/full parser, K≥2 atomic footprint 조건, namespace v2 8640 trials와 matched-seed 통계는 완료했다. E3 main4092와 assumed latency687도 완료·raw audit를 통과했다. 결과와 신뢰구간은 CERN_FOOTPRINT_REPORT.ko.md, E3_CPU_REPORT.ko.md 및 SOFTWARE_INTEGRATION_REPORT.ko.md에서 구분해 읽는다.

실제 target radiation rate/physical layout과 실제 RTL latency/PPA는 측정하지 않았다. 현재 소프트웨어 범위의 추가 사용자 조치는 없다. Cadence를 재개할 때 동일 PDK/기능/조건의 실제 latency·area·energy를 측정해 이번 가정을 교체한다.
