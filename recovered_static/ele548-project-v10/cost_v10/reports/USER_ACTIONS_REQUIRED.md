# 사용자 조치와 blocker

## 지금 조치가 필요 없는 항목

설치·권한·license·PDF·SPEC 경로에 관한 미해결 요청은 없다. 이번 실제 Genus/Innovus/Xcelium checkout 및 기능 gate가 완료됐다. 기존 HW1·R2 source/config/binary/result를 바꾸지 않았다. TCAD는 사용하지 않았다.

실패한 명령은 원시 로그와 함께 보존했고 아래처럼 해결했다. 사용자에게 이를 다시 수행하라고 요청하지 않는다.

|실제 실패|시도한 수정/결과|
|---|---|
|protection_rtl_A1: module helper/public 이름 충돌|helper 이름 수정, A2 실제64,155행PASS|
|genus_preserve_probe_A1: unmapped leaf `.preserve true` TUI210|설치 공식문서의 merge/delete 속성, A2 실제24FF 보존PASS|
|map_secded_A1: report_timing의 unusedQN startpoint TIM303|새A2 flow에서 sequential instance query만 변경,467FF exportPASS|
|gls_p0_A1: UDP output net deposit의 post-edge mismatch|원시FAIL 유지, 별도Q-clamp-through-edge/release fixturePASS. 내부UDPstateSEU로 주장하지 않음|
|overwrite_rtl_A1: root launcher가TB의두참조파일누락(CUVMUR)|실제filelist의recurrent/direct 의존파일추가, RTL변경없이A2PASS|
|C++ warning 및 nested test-cell/Q/QN parser 경계|구체적수정1회씩보존,최종해당gatePASS|

## 다음 CPU 실행에 필요한 승인

현재 global CPU는 **3,361/3,361회**다. 장기 유지 비교를 계속하려면 다음 묶음의 숫자 승인이 필요하다.

- 주 실험108회: clean36+conditional SOURCE SBU72. 그 안에 정상/오류 gate12회가 포함된다.
- 원인 수정·회귀 reserve6회. 최대 새114회이므로 **global3475회** 제안.
- 실제 과거속도와R8선형가정에 따른 후속예상5~10core-hours. 후속hardcap10, **v9+v10+후속recorded16core-hours** 제안. global108core-hours는 유지한다.
- 완료한 component round2core-hours/512MiB는 그대로 봉인한다. 후속namespace384MiB, v9와새worktree합계8GiB/전체34GiB/free10GiB/공유최대32slots도 유지한다.

수치 승인이 필요한 근거는 사용자가 이전에 확정한3361회 상한과, 새 [연구 규약 §10](/home/youns/workspace/ele548-project-v10/cost_v10/sources/research_charter/BP_SEU_Codex_Research_Charter_v10/GOAL_AND_RESEARCH_LOOP.ko.md)의 “이 goal 요청은 그 승인을 대신하지 않는다” 규칙이다. 최대32core 허용은 trial 총량 확대와 다르다.

이는 새macro·PDK·license 확대 요청이 아니다. 기존R2 gem5 binary/config와 native검증된persistent wrapper를 읽기만하고 새 namespace에만 결과를 쓴다. 실제native6개는PASS지만 아직새gem5결과는없다. 새격리runner 준비상태는 NEXT_NATIVE_LIFETIME_PLAN과 후속 READINESS를 기준으로 확인한다. 승인 전에 fault tape 생성·gem5 발행·기존실행변경을 하지 않는다.

## 승인 없이 계속 가능한 일

기존 자료·문헌·입출력/owner/예산 검사, 격리runner의 dry-run/guard 검증, overwrite primitive 통합 설계 준비가 가능하다. CPU 한도 때문에 source/RTL 기능 PASS를 gem5 성능 PASS로 바꾸지 않는다. task-marker72안은 미구현 구상이며 승인 요청의 실행 가능한 대체물로 쓰지 않는다.

최신 승인 보완: 사용자가 “3,475회·16 core-hours로 확대하고 진행”이라고 명시 승인했다. native_lifetime_next/runtime/configs/BUDGET_AMENDMENT.lock.json에 기록했다. 이전 승인대기 표시는 작성 시점 기록이며 현재는 후속 정확성/속도 gate 후 실행한다. 완료한 component 원시 결과와 producer는 변경하지 않는다.
