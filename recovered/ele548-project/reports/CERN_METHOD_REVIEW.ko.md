# CERN 군집 원문 검토와 사용 범위

SOURCE FACT: [공급자 Zenodo 8314389](https://zenodo.org/records/8314389)는 CY62167GE30-45ZXI 65nm commercial SRAM의 proton/heavy-ion MCU 자료이며 내부 ECC를 끈 상태라고 설명한다. 군집 추출 방법으로 2014/2015 논문을 지정한다. 취득한 세 파일은 공급자 MD5와 전체 문법 검증을 통과했다.

추가 원문 L08은 [Coronetti et al., REDW 2020 accepted manuscript](https://jyx.jyu.fi/bitstreams/e328580f-8d6c-478d-b815-f1b59fa07728/download)이다. PDF p2–3의 device table과 시험 조건을 검토했다. L09는 [2015 clustering 방법의 저자 Bosser의 박사학위 논문](https://jyx.jyu.fi/bitstream/handle/123456789/56348/1/A_Bosser_%20Doctoral%20thesis_%20v12_FINAL.pdf)이다. PDF p50–57을 검토하고 p53/p57의 이미지를 확인했다. 일반 공개 HTTPS GET으로 취득했으며 접근 제한을 우회하지 않았다. 이 두 문서의 hash/버전/페이지는 sources/cern_methods.lock.json에 고정한다.

SOURCE FACT (L09 p51–57): TIGER는 개별 오류와 cluster 목록을 만들고 cluster의 공간·시간 경계를 저장한다. 검출 시간과 공간적 근접 기준에 따라 오류를 차례로 묶는다. 순차적인 type C 오류를 먼저 분리하고 나머지를 분류한다. Type A에는 singleton SBU도 포함된다. 저자의 예시에는 여러 원인이 합쳐져 잘못 분류된 군집이 있다. 따라서 coordinate count는 cluster 내 오류 좌표 수이며, particle count와 동의어가 아니다.

L09 p57의 10 horizontal / 67 vertical / 2 seconds는 **해당 SRAM90 예시**의 설정이다. 이번 65nm 세 파일의 설정으로 옮기지 않는다. 두 standalone 2014/2015 논문은 아직 확보하지 못했고, 세 파일을 만든 구체적 코드·threshold·singleton 완전성·cluster0(0,0)의 의미는 확인되지 않았다. 검토한 primary thesis는 일반 grouping 방법과 한계를 뒷받침한다. 데이터셋별 모든 방법을 재검증했다고 주장하지 않는다.

DESIGN HYPOTHESIS: 공간 패턴 시험의 모집단을 파일별 **기록된 K≥2 군집**으로 고정한다. 군집 하나를 uniformly resample하며 모든 unique 좌표와 K를 한 atomic event에 유지한다. 조건별 파일을 섞지 않는다. Proton 두 조건에서는 K=2, Ar1050에서는 K=2…12이다. 이 조건부 표본으로 P(MCU), per-bit/second rate, 독립 입자 충돌 수를 추정하지 않는다. Singleton 및 origin-flagged rows는 원본·audit에 모두 보존하며, K≥2라는 명시적 모집단 밖에 있을 뿐이다.

ASSUMPTION: 실제 TAGE 배치가 없으므로 16×22 논리 tile에 동결된 S* 346 bits를 bijection으로 놓고 6개 남은 cell은 빈 공간으로 둔다. Word-contiguous 배치, round-robin word-interleaved 배치, 동일 K의 dispersed 대조를 비교한다. 원 coordinate offsets를 좌표 단위 그대로 옮기되 tile 밖/빈 cell을 건드리는 translation은 선택하지 않는다. 군집 크기를 줄이거나 wrap/clip하지 않는다. 이 조건부 fit 모델은 물리 pitch, irradiation footprint, target chip topology가 아니다.

Repeated clock은 independent Poisson을 conditional-branch 좌표에 가정하며 λ=10⁻³을 stress 설정으로 선언한다. Equal-event와 equal-expected-flip λ/E[K]를 구분한다. Source의 clock labels를 target arrival clock이나 CPU seconds로 환산하지 않는다. S*와 holdout은 E1에서 동결한 것을 그대로 쓰며 별도 seed를 사용한다. 보호 추가 bits는 이 targeted-payload 시험에서 제외하고 E2/E3의 별도 full-population 시험으로 다룬다. TMR replica0만 노출하므로 이 시험의 TMR 결과로 spatial replica isolation을 증명할 수 없다.

검증·실험 산출물: data/curated/cern_footprint_model_card.json, configs/cern_footprint.lock.json, scripts/run_cern_footprints.py, reports/CERN_FOOTPRINT_PILOT.json 및 후속 main/summary. CPU 성능은 별도 gem5 결과이고 실제 RTL timing/PPA는 유예한다.
