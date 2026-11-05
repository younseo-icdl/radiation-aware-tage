# 사용자 행동과 현재 blocker

현재 compiler/library/license/dataset/network 요청은 없다. v11에서 승인한 오류12회는 이미 완료돼 CPU 장부가3487/3487이며 v13 새 CPU는0이다. 그12회를 중복 실행하지 않았다.

실제 실패 명령은 `.../python -B undo_packet_v13/tools/gate.py lookup --attempt A2`다. Compile은 exit0, run은 exit1(`FAIL trained pinned provider mismatch`)이었다. 확장 test fixture가 path-bit에 고정 `pc>>2`를 썼지만 standalone pinned params는 instShiftAmt=0인 것이 원인이었다. 실제 config의 `pars.instShiftAmt`로 fixture만 수정한 한 번의 concrete fix 뒤 A3에서 정상/훈련/의존성/metadata/wrap gate가 통과했다. A2 binary/source/실패 로그는 보존했다. 사용자 수정은 필요 없다.

현재 구조 blocker는 timed BPU의 연속 squash admission·finite credit·올바른 재시도와 full protection staging이다. 새 clock adapter의 object compile을 전체 BPU/O3 PASS로 보고하지 않는다. 상세 NEXT_GEM5_CONNECTION.ko.md. 이 구현·검토는 남은 preparation 예산에서 계속할 수 있으며 아직 준비되지 않은 CPU 실행 수 승인을 요청하지 않는다. 실제 통합 producer/gate를 준비한 다음 필요한 CPU 횟수·시간·저장량을 산정한다.

RTL/Cadence/SPICE/TCAD 실행은0이다. 기존 성공/실패·holdout·source/config/binary/archive는 보존한다. 전체 research goal은 active이며 성능–비용 승자는 아직 미확정이다.
