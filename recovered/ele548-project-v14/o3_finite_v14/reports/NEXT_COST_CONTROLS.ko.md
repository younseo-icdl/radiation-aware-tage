# 다음 최소 대조 — 설계 가설, 아직 실행하지 않음

이 문서는 새 CPU 결과나 새 후보의 성공을 주장하지 않는다. 현재 승인된 CPU24가 끝난 뒤 사용할 최소 대조이며, failed-stage reserve2를 새 실험에 쓰지 않는다. 기존 S*=346의 P0/P_ED(빈번·주기 구별)/ECC/TMR과 원래 native·직렬 결과를 보존한다.

## 관측과 경쟁 설명

IMPLEMENTED/TESTED RESULT: 현재 source/provider는 독립 PC의 II1·복수 pending을 지원하지만 실제 Fetch는 기존 single instruction/token과 next-PC 대기를 유지한다. 실제 CPU의 lookup pending 최대1과 별도의 source pending을 구분한다. Qsort의 같은 L에서 Direct cycles가 작은 현상은 source dependency/복구 방식 차이와 같은 방향이지만, counter 합계를 인과 기여도로 쓰지 않는다.

SOURCE FACT: [BPredUnit::predict](/home/youns/workspace/ele548-project-v9/third_party/gem5-native-v9r2/src/cpu/pred/bpred_unit.cc:122)는 unconditional의 방향을 true로 정하고 conditional에만 direction lookup을 한다. 그 뒤 기존 BTB/RAS/indirect target policy를 적용하며 target이 없으면 predTaken을 false로 바꿀 수도 있다. 따라서 unconditional을 실제 taken outcome과 같다고 가정해선 안 된다. [TAGE::updateHistories](/home/youns/workspace/ele548-project-v9/third_party/gem5-native-v9r2/src/cpu/pred/tage.cc:132)는 unconditional의 BranchInfo를 만들고 최종 예측 방향으로 history를 갱신한다. 현재 v14는 모든 control에 대해 source fold/provider 응답을 기다린다.

NEW DERIVATION: 완료된 Direct/L1의 BPU 총 lookup 중 conditional 외 비율은 qsort 30.49179084%(538,378/1,765,649), dijkstra 11.40142989%(356,342/3,125,415)다. 원시는 각 CPU output의 stats.txt이다. 이 비율은 제거 가능한 cycle 비율이나 최적화 이득의 상한이 아니다. target/history 준비와 squash 비용을 포함하지 않은 호출 구성 통계다.

## 대조 1: source update 고정, query L만 변경

DESIGN HYPOTHESIS: 현재 L2−L1 차이 일부는 read latency가 아니라 update publication/RMW 경로에서 나온다. 공통 source update L=1, II=1과 동일 finite ports를 유지하고 REC의 query L만1→2로 바꾼다. provider extra1은 유지한다. Direct의 기존 L1/L2는 update가 이미1이므로 참고할 수 있다. 필요하면 OW에도 같은 대조를 추가한다.

최소 CPU 후보는 REC(query2,update1)의 checksum1 + 기존 세 R1 프로그램3이다. 기존 query1/update1과 query2/update2를 함께 읽는다. 이4회는 아직 승인된 CPU24의 구성원이 아니다. 구현 전 config에서 두 parameter를 분리하고, C++ equality·source version/forwarding·query stage visibility·squash·중간 SEU gate를 확인한다. 새 config/producer/output을 동결한 뒤 실행량·시간을 산정한다. Lookup과 journal/RMW의 효과를 섞지 않는다.

## 대조 2: unconditional의 필요한 state만 기다리는 경로

DESIGN HYPOTHESIS: 방향이 상수인 control에도 전체 folded history/table 응답을 기다리는 것이 불필요한 비용일 수 있다. 원래 BTB/RAS/indirect target policy와 history checkpoint 소유권을 유지하면서, 실제로 이용 가능한 target·최종 예측 방향·이전 path/source version을 사용하는 유한 fast path 또는 forwarding을 검토한다. 조건을 충족하지 못하면 기다린다.

이는 아직 구현하지 않았다. 향후 fast path가 단순히 fold query를 생략한다면 **unconditional fast path 효과**로 보고하고 복수 lookup 중첩 효과라고 부르지 않는다. 기존 BPU target miss/fallthrough/RAS rollback을 바꾸거나 미래 실제 outcome을 쓰는 구현은 허용하지 않는다. 새 path checkpoint/token/late-ACK storage와 ports를 manifest에 넣고, commit 전에 실제 state가 준비되도록 stall해야 한다. 이 경로를 REC와 Direct 모두에 주며 나중에 보호 기준선에도 같은 조건을 적용한다.

## gate와 판단

다음 PC와 history를 미리 제공하는 독립 component throughput test는 계속 별도다. 실제 branch stream에서는 기존 예측 target/방향만 사용하고 발행·완료·cancel·pending, source publication과 retire gate를 함께 관찰한다. Queue full, back-to-back RMW의 최신 값, squash/stale response, wrap, mid-repair SEU, source 검증 실패와 metadata DUE를 다시 검증한다.

정상 output·committed identity·알고리즘/update 정책을 확인한 뒤 작은 pilot을 거친다. 새로운 clean 비용이 확인되기 전에는 보호 성능 우위로 확대하지 않는다. Fault schedule binding과 동일 resource의 P_ED/ECC/TMR controller staging을 완료한 다음에만 SOURCE와 WHOLE을 분리한 A/B/C/D·paired B−D·독립 평가를 진행한다. RTL/Cadence/SPICE/TCAD는 이 계획에 포함하지 않는다.
