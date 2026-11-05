# v15 준비 결과 — 실제 CPU 실행 전

DONE: 별도 `codex/v15-query-unconditional` worktree와 producer에서 query/update latency 분리와 unconditional early-direction/late-checkpoint 경로를 구현했다. 기존 v9–v14 source/config/binary/raw/실패/holdout은 보존했다. 새 gem5 CPU 실행은0이며 global3511/cap3513이다.

SOURCE FACT: pinned [TAGEBase::tagePredict](/home/youns/workspace/ele548-project-v9/third_party/gem5-native-v9r2/src/cpu/pred/tage_base.cc:371)는 unconditional이면 history/table를 읽지 않고 true를 반환한다. [BPredUnit::predict](/home/youns/workspace/ele548-project-v9/third_party/gem5-native-v9r2/src/cpu/pred/bpred_unit.cc:122)는 그 뒤 원래 BTB/RAS/indirect 정책을 적용하며 target이 없으면 fallthrough로 바꿀 수 있다. 새 경로는 이 코드를 바꾸지 않았다. 실제 outcome을 미리 사용하지 않는다.

IMPLEMENTED: uncond request도 실제 finite source/provider 작업을 수행한다. 방향만 먼저 전달하고 token/PC/valid가 보호된4개 owner slot에서 실제 path checkpoint를 기다린다. Actual late response가 CPU BI path에 도착하기 전에 retirement와 squash를 보수적으로 막는다. Cancel도 이미 claimed된 checkpoint를 보존한다. Full1000 source credit 상태에서도 checkpoint completion은 추가 append credit 없이 진행한다. Conditional은 실제 예측 결과를 기다린다. Source query L과 update L은 독립 parameter이며 source/query/ACK/response 포트와 II1 조건은 유지했다.

DONE gate:

- `tools/gate.py query_gate --attempt A1`: update1/query1·2, pinned TAGE23052 controls/720 nested squash, ingress metadata430 SBU, wrap53 PASS.
- `tools/gate.py early_gate --attempt A2`: native/train13008 controls/720 squash, added metadata848 SBU, expected DUE1, tiny ID/epoch wrap1944, mid-repair·queue-full·stale cancel·full-credit·실제 path-latch SEU 전파 PASS.
- `tools/build_cpu.py --attempt A1`: 새4 object + unchanged1512 object를 새 ELF에 link, `--build-info` PASS. 실제 ELF SHA는 `ffd9d1013f9dc567e84b984dce799626fa3609e276c0b91cddd2d66c4921854c`.
- `tools/initialize.py --attempt A1`: 15설정의 실제 O3 object를 tick0에서 instantiate, source cycles/committed ops/accepted0와 no-simulate AST gate PASS. CPU 기능/성능 PASS로 해석하지 않는다.
- `tools/micro.py`: 실제 산술 결과를4096과 검사한 native jump-chain checksum PASS. 3uncond+1cond가 한16-byte block에 있는 것은 objdump로 확인했다. Synthetic microbenchmark이며 HW1 대표 workload가 아니다.

| C++ REC128개 dependent control | query1/update1 | query2/update1 |
|---|---:|---:|
| 기존, uncond prediction 완료 cycle |637|765|
| early, uncond prediction 완료 cycle |127|152|
| early, 실제 checkpoint 완료 cycle |131|157|
| early, 실제 retirement 완료 cycle |258|284|
| conditional prediction 완료, 양쪽 동일 |637|765|
| lookup 최대 진행 수, 기존/early |1/4|1/4|

이 표는 실제 C++ stage 동작이며 CPU IPC 개선을 뜻하지 않는다. Actual gem5 next-PC/BTB/Fetch와 프로그램별 비용은 아직 실행하지 않았다. A1 기능 gate는 통과했지만 peak를 consume 뒤에만 측정해 plain을0으로 과소측정했다. 원본을 보존하고 A2에서 admission/edge 측정 및 추가 fixture로 수정했다. 이전 숫자를 CPU 결과처럼 쓰지 않는다.

VERIFIED ASSUMPTIONS / 범위: 추가848 physical logical bits는97-bit owner word4개의 two-copy SECDED와 cancel control이다. 실제 logical manifest에서 모두 열거하고 단일 bit를 검증했다. PC64/token32/valid가 들어가며 decoder/writeback4경로의 정상 stage-fit은 가정이다. Source/update/query와 provider latency도 실제 PDK 측정값이 아니다. Global checkpoint retirement/squash barrier는 보수적 선택이며 최소 비용 주장이 아니다.

CPU-owned BI payload와 simulator host-pointer association은 fault 범위에서 제외했다. Host pointer 자체를 logical bit로 주입하지 않는다. **실제 CPU 소비자의 token→branch-record routing 저장소와 late path write port의 hardware 비용/metadata 오류는 아직 검증하지 않았다.** 이 인터페이스 비용이 구현에서 추가될 수 있다. Predictor/controller manifest 전체와 CPU 전체 fault scope를 혼동하지 않는다. 이 불완전한 interface로 hardware 후보를 qualified 처리하지 않는다.

NOT DONE: 새 O3 functional execution/실제 요청 중첩/프로그램 cycles·IPC, source protection controller staging, CPU fault binding, SOURCE/WHOLE A/B/C/D·B−D·paired CI/독립평가, consumer routing의 hardware 비용. 기존 동일S*=346 P0/P_ED/ECC/TMR은 계속 필수 비교군이며 새 prototype이 대체하지 않는다. RTL/Cadence/SPICE/TCAD 실행0이다.

NEXT: `CPU18_PROPOSAL.lock.json`의 실행18개가 준비됐고 default dry-run은 CPU를 발행하지 않는다. Existing backward checksum2 → synthetic CPU micro4 → candidate checksum3 → qsort/dijkstra/SHA1 후보9 순서다. Micro에서 실제 중첩이 확인되지 않거나 early 정확성이 실패하면 early workload를 실행하지 않고 independent query-only control을 계속한다. 실패와 invalid pair는 보존한다.

BLOCKER: 현재 남은2회는 failed-stage 회귀 전용이다. 새18회에는 현재 CPU/시간 배분을 사용할 수 없어 추가 범위 승인이 필요하다. 제안은 CPU3513→3531(새18+기존reserve2 유지), v11 이후5→8coreh, v9 이후16→19coreh, 새 CPU phase 최대4coreh다. Global108coreh·disk320MiB/all7roots8GiB·공유32slots는 유지한다. 예상1.5–3.5coreh는 planning이고 실제값이 아니다. Timeout/예약/단계 gate와 모든 입력·seed·명령은 동결했다.
