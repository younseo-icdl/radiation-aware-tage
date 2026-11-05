# G3 정확성·설계 pilot

최종 정책의 standalone C++ gate는1,089cases PASS. 추가로419cases에서 기존4방법의 faultful equality, drain 전 publish 금지, 진행 중 committed source/codec/accumulator/parity 및 control bit 주입을 검증했다. SECDed3payload-errors→self-consistent wrong result는 EXPECTED_COVERAGE_FAILURE로 보존했다. Active control cursor 오류는 liveness를 검사하며 모든 corruption을 정확히 복구한다고 주장하지 않는다.

C++ design 초기418회 및 코드리뷰 수정 후 final418회를 각각 보존했다. 같은 snapshots/events를 재검증했으므로836개의 독립 samples라고 합치지 않는다. Selection rule20*net+checks+rebuild_steps는 탐색 proxy이며 hardware energy나 gem5 cycles가 아니다. Final selection N1k64, H1k32는 새 CPU 결과를 보기 전에 동결했다. H_REV도 design control로 실행했다.

결함 기록: 첫 compile의 Snapshot type 변환 오류1회; primary/shadow DUE reset 후 현재 actual branch를 유지하는 순서 code review fix; 최종 healthy/fault property 재검증. Runtime model의 token queue overflow는 G4에서 별도로 다룬다.

재현 명령과 원시 log: `G3_BUILD*.log`, `G3_CORRECTNESS*.log`, `G3_PROPERTIES.log`, `G3_CPP_SCREEN_FINAL.json`, `cpp_screen_final/*.csv`. 현재 FPGA/RTL/합성 검증은 수행하지 않았다. Added physical logical cells는 Controller manifest와 gem5의 maintenance12bit 추가를 함께 확인해야 한다.
