# 기본 보호 비교 이후: 주기적 history 검사 확장

상태: C++ 정확성/84회 design pilot/96회 조건부 source-pattern holdout/실제 O3 checksum13건 완료. 고정 k=32의 실제 프로그램42회 평가와 최종 matched-seed 분석은 진행 중이다. 아래 방법은 구현한 탐색용 software policy이며 actual RTL/PPA 우위를 검증한 결과가 아니다.

## 최신 기준선과 선정 근거

최신 corrected E3 main4092와 latency687 및 해당 raw hashes를 확인했다. 기존 main selected-payload CHARM6T qsort P0 slowdown10.3891902%는 원본 summary의 값이다. 새 비교는 다른 evaluation owners의 기존 latency 결과를 정확히 재사용하므로 이10.39%를 새 B−D의 비교값으로 사용하지 않는다. 기존 S*346bits, P0/P_ED/P_ECC/P_TMR, source pin/알고리즘/기존 producer binary는 유지했다.

SOURCE FACT: L01 ICCD2003은 speculative branch prediction의 graceful degradation/부호화 비용을, L02 ICCD2009 SectionVII는 performance fault의 보호 가능성을 논의한다. L02의 permanent-fault 설정은 이번 transient SEU와 구분한다. [L13 Scatter Scrubbing](https://cfaed.tu-dresden.de/files/Images/people/chair-pd/Papers/08875431.pdf) p1–3은 scrubbing 및 비용을 고려한 scheduling을 다루며 ideal overhead0 결과가 실제 overhead에서 바뀔 수 있음을 보여 준다. FPGA configuration/golden bitstream 기법을 TAGE에 그대로 옮기지 않는다. [L14 원 TAGE 논문](https://jilp.org/vol8/v8paper1.pdf) p1은 여러 history-length components의 역할을 설명한다. 검토 범위·hash는 periodic_literature.lock.json에 있다.

주기 검사/parity 자체는 기존 연구다. 참신함이 입증됐다고 주장하지 않는다. 이번 질문은 TAGE 상태를 계속 update/rollback하면서 검출을 늦춰도 오류 흔적을 유지할 수 있는지, 그때 정상 response 비용과 delayed-damage tail이 어떻게 바뀌는지다. Adaptive/history-rebuild는 아직 구현·검증하지 않은 후보로 남긴다.

## DESIGN HYPOTHESIS · IMPLEMENTED/TESTED

첫 추가법 P_PERIODIC_ED는 같은23 history words/346payload bits에 parity를 유지하고 k개의 legitimate history-write callbacks 후 첫 prediction-read boundary에서 검사·복구를 결정한다. Speculative update, correction, 변경이 있는 discard/rollback 및 실제 refill writes가 count에 포함된다. Commit-only callback은 history를 쓰지 않으면 count하지 않는다. k=0은 legacy behavior, k=1은 새 boundary policy이며 모든 fault timing에서 기존 P_ED와 동치라고 주장하지 않는다.

Unchecked write를 정상처럼 재인코딩하면 SEU 흔적이 사라질 수 있다. 이번 규칙은 각 word의 기존 residual을 유지한다. D_old/D_new는 실제 저장 data, p는 sidecar parity라고 하면 p_new=p_old XOR parity(D_old) XOR parity(D_new)다. 따라서 legitimate atomic write에서 parity(D_new) XOR p_new = parity(D_old) XOR p_old가 된다. Injector 사건 목록/golden data는 controller에 전달되지 않는다. 기존 logical-sidecar XOR primitive는 이 legitimate update에도 사용하며 외부 fault event로 기록하지 않는다.

이 규칙은 odd residual을 후속 RMW/rollback을 통해 보존하지만, 자연 회복 후에도 residual이 남아 보수적 reset을 일으킬 수 있다. 같은 word의 even errors 및 후속 XOR cancellation은 검출되지 않을 수 있다. 다운스트림 학습 오염은 검사·reset으로 자동 제거되지 않는다. 기존 epoch/refill130actual-commit/drain 규칙을 사용해 reset 이후 오래된 speculative records의 복원·학습을 억제한다.

추가 progress counter8bits는 실제 logical FI manifest와 테스트에 포함했다. 총bits는 C++65441, CPU65442이며 target payload 비교는 여전히346bits다. k는 configuration/synthesis constant다. Atomic update 내부 before-write residual23bits는 transient scratch이며 serialized RTL의 registers/ports/arbitration 비용은 별도 측정해야 한다. Shared SET/CPU queue·checkpoint/transport 등 기존 제외도 유지한다.

정상 검사 지연C는 due prediction read에만 부과한다. Update 시 parity/residual 유지 연산은 매번 수행하고 delta_word_reads/sidecar_reads/parity_operations를 별도 계수한다. 현재 추가 update-lane response latency는0으로 가정했다. **전체 보호 연산이나 에너지가 1/k로 감소한다고 주장하지 않는다.** R=4의 실제 response-port hold와 arrival clock을 유지한다. 실제 회로의 delay/throughput/energy는 미측정이다.

## 선택·평가 계약

C++ design84는 HW1 기존 design prefix의2개 trace, k=1/8/32와 네 기준선을 사용한다. Selection proxy는20×net extra misses+1×checks이며 cycles 단위의 탐색용 가정이다. Workload와 single/repeat family를 동일 가중하고 최소 후보를 선택해 k=32를 동결했다. 이 proxy는 measured gem5 cycles가 아니다. 더 넓은 k grid의 최적이나 CPU-optimal 선택을 주장하지 않는다.

이 pilot의 exposure window는 anchor500k부터100k conditional branches다. Single event는 window의 첫20k 안에 있어 post-event 잔여 관측은80k–100k이며 같은 seed의 모든 방법은 동일 event/window를 사용한다. 기존 E1의 동일 post-event horizon/S* 선정은 재실행·변경하지 않았다. Single damage의 finite observation/censoring을 보존한다.

CPU 평가42는 qsort/dijkstra 각 clean1, repeated10, raw/folded single 각각5회다. CPP-design125480000 owners와 CPU repeat115480000/single105480000 owners는 분리한다. 이미 관측한 고정 programs/기존 baseline evaluation seeds를 재사용하므로 완전한 workload-blind 일반화 시험이라고 주장하지 않는다. Native 정답, 실제 instructions/cycles/MPKI 및 schedule·priority·XOR·repair semantics를 확인한다.

CERN/Flying holdout96은 기존 corrected disjoint trace 입력과 source schedules를 그대로 재사용한다. CERN72회는 파일3/가상mapping3/single·repeat2/seed2/workload2이며 Flying24회는 duplicate정책2/time3/seed2/workload2의 SBU 설정이다. 선택 owners와 겹치지 않는 Flyingn2/n3, CERNn0/n1만 사용한다. 추가 k tuning을 하지 않는다. 이 결과는 branch-trace 모델 민감도이며 실제 CPU cycles가 아니다. Source thresholds/입자 identity/물리 rate/layout 및 시간 압축 한계는 그대로 유지한다.

## NEW DERIVATION — 근사와 실제 비교

A=P0 clean, B=P0 faulty, C=own protected clean, D=own protected faulty다. 순이득은 raw B−D와100(B−D)/A이며 B−D=(B−A)−(C−A)−(D−C)다. Fault loss100(D/C−1)와 clean overhead100(C/A−1)는 단순히 더하지 않고 total slowdown100(D/A−1)를 직접 계산한다. Helpful/zero effects를 보존한다. Matched trial seed를 program 안에서 bootstrap2000하고 고정2program 평균에 동일 가중한다. 실패를 attempted 분모에 남기고 수치 평균은 normal-exit에 조건화한다.

탐색 근사 J(k)=c/k+λd k/2는 λ를 **event/history-update**, c를cycles/inspection, d를cycles/event/delay-update로 해석한다. 균일·독립 arrival phase에서 E[wait]=k/2고, 양의 c,λ,d라면 continuous k*=sqrt(2c/(λd))다. Integer/finite-grid opt와 workload-dependent update/cycle rate는 별개다. λd=0 또는 helpful effects로 effective d가 음수인 경우 이 interior optimum을 사용하지 않는다.

Toy Monte Carlo는 uniform-phase mean과 Poisson count mean/variance를 검증한 별도 가정 시험이다. 실제 TAGE는 자연 회복·residual 유지·even cancellation·학습 오염·speculative callbacks·variable update cadence가 있어 같은 선형J를 확인했다고 주장할 수 없다. CPU λ/cycle와 C++ λ/conditional-branch를 물리적으로 환산하지 않는다.

Single-event tail은 실제 첫 detector delay, D−C 및 B−D의 관측 p50/p95/max와 censor count를 보고한다. Field/program당5seed의 p95는 모집단 보장이 아니다. IID 가정조차5개 sample maximum이 population p95 이상일 확률은1−0.95^5≈22.6%다. Nonparametric one-sided95% coverage에는 최소59samples/group이 필요하지만 이는 이번 작은 pilot 범위 밖이며 adaptive policy 개발이나 worst-case 증명이 아니다.

## NOT DONE · NEXT

최종42회 결과/CI/그림을 완료 후 여기에 반영한다. 실제 RTL latency/PPA 및 추가 update-lane 비용, 더 넓은 grid·tail confirmation, Adaptive/workload-confusion 테스트, protected-raw folded rebuild는 미완료다. 기존 세 보호법은 계속 기준선이다. Cadence는 보류하고 TCAD는 사용하지 않는다.
