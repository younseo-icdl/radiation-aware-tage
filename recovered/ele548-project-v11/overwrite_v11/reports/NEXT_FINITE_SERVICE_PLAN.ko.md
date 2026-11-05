# 다음 비용 gate: 같은 source 소유권과 실제 stage

이 문서는 **DESIGN HYPOTHESIS / 다음 구현 계획**이다. 실행한 CPU latency 실험이나 구현 완료 보고가 아니다. 이번 overwrite는 stored fold를 읽고 actual history 전환마다 full reduction을 수행하는 synchronous C0 통합이다.

## 관측과 경쟁 설명

`CPU_NORMAL_ACTIVITY.csv`의 실제 forward+undo 수를 조건부 lookup 통계와 연결했다. 정상 R8에서 full-fold 작업/conditional lookup은 qsort1.7500, dijkstra1.3557, sha1 1.0437이었다(`NORMAL_COST_PROXY.json`). 모든 lookup을 분모로 한 약1.21/1.21/1.00보다 크다. Unconditional 갱신과 undo도 full reduction을 수행하기 때문이다.

Direct의 비교 값은 **conditional lookup당21-fold set**이라는 lookup-only proxy다. Surprise branch의 추가 index/tag 계산과 진단용 hash 호출까지 세는 actual total direct-work counter는 아직 없다. 이 비율을 실제 에너지 비율이나 지연 개선으로 쓰지 않는다.

경쟁 설명은 (a) lookup reduction이 critical path를 지배하므로 update 이동이 유리할 수 있음, (b) source supply·full reduction·200bit 쓰기·undo 작업이 더 비싸 불리함, (c) 현재 C0가 source/visibility 비용을 무료로 두어 차이를 가림이다. 유한 service 없이 이 설명들을 CPU 결과로 분리했다고 하지 않는다.

## 먼저 맞출 source 경계

현재 recurrent/overwrite는 inherited software raw buffer와 pointer를 사용하고 direct는 별도 finite ring/rollback journal/head/FIFO를 노출한다. 같은 raw130 조건부 사건의 functional 비교와 전체 물리 source 비용 비교는 다른 계약이다. Fold200 제거/추가만으로 전체 storage·에너지를 비교하지 않는다.

다음 producer에서는 source retention·rollback 소유권·capacity·source read/write ports를 공통 경계로 맞춘다. 실제 필요한 undo 범위를 명시하고 공간을 쓰기 전에 credit을 예약해야 한다. 관측 최대 occupancy에 단순 여유를 더한 값은 overflow 불가능의 증명이 아니다. 기존 source-head/FIFO의 lossless correction/실패 기록을 보존한다.

## actual stage 구현 조건

1. Source 전환을 받아들이는 시점, source operand를 읽는 시점, full/recurrent 계산 단계, fold 결과 공개 시점을 별도 명시한다. 계산을 먼저 완료하고 debt를 나중에 청구하지 않는다.
2. L과II를 분리하고 유한 input/output storage·포트·backpressure를 구현한다. 이미 수락한 history/undo를 버리거나 FIFO overflow를 무영향 오류로 분류하지 않는다. 불필요하게 모든 callback을 직렬화하는 극단도 피한다.
3. 다음 PC/history가 이전 예측에 의존할 때 실제 response까지 기다리거나 검증 가능한 forwarding을 사용한다. 독립 요청 II=1 gate와 dependent branch-stream throughput을 구분한다. Pipeline만으로 latency 손실이 사라진다고 가정하지 않는다.
4. Squash/rollback의 ID/epoch/freshness를 실제 저장하고 stale 결과·training이 새 상태를 덮지 않게 한다. Wrap 때 drain/ACK 없이 epoch를 재사용하지 않는다. Mid-stage SEU·stale source operand·queue-full·반복 RMW·source 검증 실패를 시험한다.
5. Raw snapshot을 요청마다 복사하는 구조라면 그130bits×depth, 응답 fold latch200bits×depth와 ID/control이 추가 비용이다. 기존 source Q를 직접 쓰는 구조라면 해당 값이 stage 동안 바뀌지 않는 소유권/II 보장이 필요하다. 아직 하나를 선택/구현한 것이 아니므로 임의의 무료 snapshot/port를 넣지 않는다.
6. Fold를 읽기 전까지 보이지 않는 연속 source 전환을 합칠 수 있는지는 별도 가설이다. Prediction뿐 아니라 surprise-branch 재계산·훈련·검사·rollback의 read barrier도 포함해야 한다. Injector event를 보고 합치거나 유리한 사건을 건너뛰지 않는다. Coalescing 가능한 작업량은 다음 진단으로 측정할 항목이며 현재 counter에서 확정하지 않는다.

## 비교와 gate

원래 native reference와 이전 serial/pipeline 결과를 보존한다. Recurrent·exact direct·overwrite에는 같은 lookup L/II/port 경계를 주고 source/update service를 별도 축으로 바꾼다. P0/P_ED(frequent/periodic)/SECDED/TMR에도 같은 source 경계를 적용한다. 구현되지 않은 방식은 한계를 표시하며 비용을 불가피하다고 단정하지 않는다.

추가 queue/latch/ID/epoch/control을 logical manifest에 넣거나 구체적 제외 사유를 쓴다. 실제 field 폭은 구현과 함께 정하고 snapshot/rollback/frame 경계를 검증한다. 기존 source-head/FIFO·native pending의 correction hold/uncorrectable 실패를 숨기지 않는다.

순서는 source/controller operation gate → no-fault 전체 상태/출력 gate → 독립/의존 request·queue-full·squash/stale/epoch-wrap·중간 SEU gate → 작은 CPU 정상 pilot → 동일 조건 fault replication → candidate/resource 고정 → 독립 input/owner 평가다. 새 CPU 수/recorded time/disk 예산은 이 구체적 producer가 준비된 뒤 산정한다. 현재 승인된3487회에 더한 새 CPU를 이 문서만으로 허가하지 않는다.

현재 overwrite가 기존 보호보다 유리하지 않은 조건도 유지한다. Functional 피해 회복을 유지할 수 있어도 필요한 source/update 지연·port·storage 조건이 충족되지 않으면 실패 조건과 비용 하한을 결과로 남긴다. RTL/Cadence/SPICE/TCAD는 계속 보류한다.
