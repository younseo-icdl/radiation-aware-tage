# v18 G2 — 실제 O3 correctness와 현재 실행

DONE: A2 최초 checksum2의 FIFO accessor 재진입 실패를 재현한 뒤 별도 B1 transaction write 경로에서 수정했다. B1 source-SBU parity2의 reset 이후 timeout은 길이0 Undo의 ordering version 미발행으로 재현했다. 별도 B2에서 원래 path checkpoint를 유지하며 완료 version을 발행하도록 수정했다. A2/B1 source/config/ELF·실패 원본을 보존했다. 알고리즘/history/hash/provider/training의 정상 의미를 바꾼 것으로 처리하지 않으며 native differential 회귀를 재실행했다.

C++ gate: B2의 scope/vector/source_guard/source_transport/transaction/zero_undo가 실제 통과했다. Native provider/training7602controls/120squash, 실제 source SBU1384, metadata37392 SBU, independent128 최대130componentcycles/최대pending3, queue-full·cancel·stale response·tiny wrap·보호 밖 retention 재진입을 검증했다. Vector even parity/SECDED3+/correlated TMR은 보장 밖의 실패 경계로 기록했다.

실제 O3: B1 여섯 방법 checksum6·micro6 PASS, micro 최대lookup pending4. SBU는 B1의 P0/ECC/TMR/Direct4 PASS와 B2 parity2 동일 조건 회귀 PASS다. B2 정상checksum2/micro1 회귀 PASS, B2 mid-stage double6 PASS다. 두 bit는 실제 RMW decoder input phase1에 연속된1tick 간격으로 주입됐다. ECC 실제DUE1/reset1/committed refill133/drain ACK1을 관측했다. 이는 conditional saboteur를 사용한 기전 gate이며 통계 campaign의 event time 생성법이 아니다.

원래32CPU gate/진단 실행의 구성은 정상 종료27·보존 실패4·의도적 short-stop 진단1이다. 원래 실패를 성공으로 덮어쓰지 않는다. B1 normal6와 B2 targeted 회귀3의 producer 차이는 G2_ACCEPTANCE에 명시했다. B2의 모든 여섯 방법을 별도program clean에서 다시 확인한다.

VERIFIED ASSUMPTIONS: 공통 source/update/check/encode/provider resource와23 병렬 lane stage-fit은 시뮬레이션 가정이다. 실제 RTL timing/면적/에너지나 hardware 안전성 qualification이 아니다. S*=346 payload 외1,000 retention bit는 정정 보장이 없으며 WHOLE에 포함한다. 새 latches/queues/ID/epoch/sidecar/replica/hold bits는 실제logical manifest에 있다. CPU-owned BI/BTB/RAS 등 제외 범위도 그대로 공개한다.

NOT DONE: 이 문서 작성 시 개발 정상 qsort pilot2가 실행 중이다. 개발102/독립408 오류·paired CI·프로그램별 최종 성능 비교는 아직 결과가 없다. 정상 overlap gate를 CPU performance winner의 증거로 사용하지 않는다.

BLOCKERS: 현재 사용자 행동이나 설치/권한 blocker는 없다. Gate 이후 승인된 상한 내 dispatcher가 진행 중이다. Auxiliary qsort launcher 형식 오류1과 B2 task-reference 준비 오류1은 각각 native 재검증/새 continuation으로 해결했으며 CPU assertion 실패와 구분한다.

NEXT: DEV_CLEAN pilot2→나머지16→같은L serial18/L2 6/native reference6→DEV fault SOURCE matched pilot2와 나머지100→candidate/resource/analysis freeze→새 입력 EVAL clean18/fault408. Owner2/8·RNG v2 role·2000events/s·WHOLE historical scale1e15·4H tape·first-exit censoring을 유지한다. Status는 tools/status.py가 실제 marker/EXECUTION 파일을 읽어 보여준다. 이 문서는 timestamp snapshot이며 실행 중 source/config/ELF는 수정하지 않는다.
