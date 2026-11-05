# G4 실제 response path의 처리량·복구 모델

수정된 synthetic gate 24개와 실제 MiBench 개발 CPU 실행 42회가 PASS했다. Checksum·정상 equality·FI XOR·epoch/fallback·실제 response hold를 검증했다. 최초 Q16 token 모델은 정상 프로그램 14개 중 4개에서 실패했고, 원시 log/source/binary를 보존했다.

수정한 resourcev2는1개의 bounded burst descriptor와12bit remaining-work counter(0..4095)로 모든 squash/commit callback 작업을 누적한다. Cycle마다1 reserved cycle만 서비스하며 새 prediction response는 debt가0일 때까지 기다린다. Counter12bits도 주입 population에 있다. 큐를 무제한으로 늘리거나 요청된 work/latency를 삭제하지 않았다. 실제 정상 프로그램의 최대 pending work는 qsort 45 cycles, dijkstra 36 cycles였다. 이 backlog가 각 물리적 port의 cycle별 요구량을 직접 측정한 값은 아니다.

계산 상태는 issue 때 atomic하게 갱신하고 response availability를 유한 service debt로 늦추는 CPU timing abstraction이다. Physical serialized RMW의 중간 register timing과 같다고 주장하지 않는다. 현재 fore-check는 historical serialC1/Q1이고 pipelined background checker는 미구현이다. Existing BI/CPU queue와 absolute scheduler timing tags는 원래의 공동 scope exclusion을 유지한다.

H1 repair는 실제 CPU history queue drain 뒤 actual-commit shadow(161coded bits) 검증, source16bits/cycle scan9단계, accumulator200+parity21검증1단계,fold21words를1word/cycle publish, 최종 source검증1단계로 총32단계다. Scan/publish는 실제 tick 로그로 제한을 검증했고 SEU clock은 계속된다. Source/accumulator 오류에 최대2restart 후 global refill을 적용한다. Legal cursor/FSM upset의 모든 피해를 복구한다는 보장은 없다.

Source validation/update logic와 in/out tap/broadcast, sidecar maintenance, source/accumulator storage, pending-work counter는 비용 contract의 일부다. Same-stage U0는 별도 가정이며 operation count가0이라는 뜻이 아니다. U1은 실제 response path에서 비교한다. Actual clock feasibility/area/energy/PPA는 측정하지 않았다.
