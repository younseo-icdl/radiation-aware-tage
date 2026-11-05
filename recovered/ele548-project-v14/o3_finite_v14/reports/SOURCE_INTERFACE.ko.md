# v14 구현 경계와 timing 의미

SOURCE FACT: pinned gem5는 v25.1.0.1, commit c8222cc67a399bfc01e8658dd14b30d5bfd634f9다. 기존 v9 binary/source/입력/holdout과 v11–v13 결과를 보존한다. 실제 실행 producer는 MEASURED_BINARY_B1.json의 SHA이며 기존 producer의 빌드 시각 문자열을 새 빌드의 증거로 사용하지 않는다. 네 object를 별도로 컴파일하고 검증된 기존 link input과 새 경로에서 링크했다.

## 실제 요청 흐름

| 경계 | 실제 operand와 공개 시점 | 유한 resource와 대기 |
|---|---|---|
| Fetch → lookup | 현재 decode된 control PC/type와 실제 request ID를 수락한다. 다음 PC가 미리 알려졌다고 가정하지 않는다. | 실제 provider context 4개. Fetch는 미완료 instruction/token 한 개를 보관한다. |
| source command ingress | 예측 방향/path append, squash에서 실제로 받은 undo/correction operand를 저장한다. | ingress 4개, source issue 1/cycle. squash callback 전에 2개를 예약한다. |
| source query/update | command 순서와 source version을 검사한 후 실제 raw/path/fold operand를 stage에 샘플링한다. | 독립 source/query 포트, II=1, 유한 command/read/response/ACK FIFO와 update/query latch. |
| source → provider | source query L=1/2를 마친 실제 fold/path 응답을 context latch에 저장한다. | 저장한 edge에는 provider를 호출하지 않는다. 다음 edge에 실제 pinned index/tag/table/provider를 계산한다. |
| provider → BPU | 실제 result latch가 phase3이 된 후 PC/type/token 소유권을 확인해 소비한다. | provider 1/cycle, result consume 1/cycle. 오래된 응답은 squash/epoch 계약에 따라 폐기한다. |
| prediction → 다음 PC/history | 원래 BPU/BAC의 예측 방향·target을 사용한다. 예측된 history append가 다음 query의 version 의존성을 만든다. | 입력/응답이 없으면 실제로 기다린다. Injector/golden/미래 실제 outcome은 사용하지 않는다. |
| squash/retire | BAC가 전달하는 원래 squash time-buffer 메시지를 유지한다. recovery-tagged source ACK가 실제 도착한 후 credit을 반환한다. | ingress 예약 실패 때만 O3 stage/time-buffer 전체를 보수적으로 hold한다. source/cache event는 진행한다. recovery ACK 완료 전 global retirement barrier도 보수적 선택이다. |

source query L과 provider 추가1은 별도다. Operand가 준비되고 경합이 없을 때 nominal ready latency는 L+1이다. 요청 수락부터 완료까지는 source version/ordering/FIFO 대기가 더해질 수 있다. Parameter 이름이 예전 pipeline과 같다는 이유로 같은 latency라고 부르지 않는다. REC/OW의 source update L도 같은 L로 바뀌고 Direct source update는 1 cycle이다. 따라서 L2−L1은 순수 read latency만 바꾼 대조가 아니다. 실제 operand publication, forwarding, undo 작업이 끝나기 전에는 완료 debt만 청구하지 않는다.

현재 clock edge에서 Controller는 먼저 Service/provider를 advance하고 그 뒤 ingress command를 Service FIFO에 issue한다. 따라서 새 command의 operand dispatch는 다음 Service edge부터 가능하다. REC/OW fold publication은 해당 실제 update stage 완료 뒤이며, Direct의 raw update와 write-first query 경로는 별도다. 이 명시적인 ingress/command/operand stage 비용을 최소 하드웨어 비용이라고 가정하지 않는다.

## 실험으로 분리한 것과 남은 것

IMPLEMENTED/TESTED RESULT: throughput_B1.json은 현재 measured_src를 새로 컴파일했다. 독립 PC 128개를 미리 아는 component 입력에서 여러 pending은 129/130 cycles, single pending 대조는 256/384 cycles이고 최대 outstanding은 각각 2/3 대 1이다. 원래 TAGE response와도 대조했다. 이는 독립 요청의 II와 반복 single-pending 대기를 분리한다.

실제 단일 thread Fetch는 기존 fetch.cc:1299에서 response가 없으면 loop를 중단하고, 그 뒤 BAC updatePC에서 다음 PC를 구한다. CPU의 실제 outstanding/완료 처리량은 CPU_ANALYSIS 최종본으로 판단한다. 현재 인터페이스에서 pending이 1이라면 **그 관측만으로** 불필요한 software pending 제한과 필요한 next-PC/history 의존성의 기여를 서로 분리할 수 없다. 가상의 독립 PC gate를 CPU 성능 개선으로 읽지 않는다.

정상 유지 비용과 branch-mispredict 복구 비용은 실제 source/query/ACK 및 recovery hold/wait counter로 관찰한다. counter 호출은 겹칠 수 있고 speculation 변화도 있으므로 합계를 정확한 CPI 인과 분해라고 부르지 않는다. 이 cohort에는 SEU 사건이 없으므로 정상 misprediction recovery와 SEU 이후 recovery를 구별해야 한다.

## logical fault 범위

각 실제 CPU output의 logical_manifest.json은 table 65,024 bits, raw ring 1,130 bits(활성130 + rollback retention1,000), path16, REC/OW fold200, source/query/ACK/provider latch·FIFO·ID·epoch·control·ingress metadata를 열거한다. 추가 ingress storage430 bits도 포함한다. L1 전체 manifest는 REC75,186 / Direct74,440 / OW74,840 bits이며 L2 stage 증가는 해당 manifest에서 별도로 읽는다. 이는 논리 저장소 수이고 합성 면적·방사선 cross-section 측정값이 아니다.

CPU-owned consumed BranchInfo/BTB/RAS/원래 time-buffer/건축 상태, allocator/RNG metadata, 절대 simulator cycle/hold helper와 diagnostic counter는 명시적으로 제외한다. helper의 history array는 provider 조합 operand scratch이며 무료 원본 복구 replica가 아니다. 새 CPU fault schedule binding은 아직 없다. 기존 조건부 S*=346 및 SOURCE raw130와 새 WHOLE storage 노출은 후속에서 별도로 매핑·검증해야 한다.

ASSUMPTION: declared L, provider1, 정상 SECDED encode/decode의 stage-fit은 software timing 가정이다. 보수적인 전체 core recovery hold와 global recovery-ACK retire fence도 최소 하드웨어 비용을 증명하지 않는다. RTL/Cadence/SPICE/TCAD는 수행하지 않는다.

## 실패와 후속 순서

기존 A1 standalone 실행은 `undo outside reserved source`로 실패했다. 실제 recovery command가 끝나기 전에 source credit을 반환하던 bug를 한 차례 수정했고, recovery-tagged 실제 ACK와 보호된 outstanding counter를 도입했다. 원본 source/binary/log를 보존했다. A2/B1 정상 equality 및 metadata/mid-repair/wrap gate가 통과해도 무제한 MCU 안전성 또는 hardware qualification을 뜻하지 않는다.

NEXT: (1) 승인된 checksum6+기존 R1 CPU18의 실제 종료·출력·hash·자원을 확인한다. (2) 같은 source update L을 고정하고 query L만 바꾸는 후속 대조, 실제 request 중첩에 필요한 legal PC/history 공급 구조를 별도 producer에서 설계한다. 아직 실행하지 않은 대조다. (3) 공통 finite-source에 frequent/periodic P_ED·ECC·TMR을 같은 sampling/ports에서 연결한 뒤 CPU fault binding과 독립 paired-owner 평가를 준비한다. 추가 CPU가 필요하면 현 cap에서 잔여량과 정확한 입력·명령·시간을 먼저 산정한다. 기존 세 복구법을 삭제하거나 Direct에만 무료 pipeline을 주지 않는다.
