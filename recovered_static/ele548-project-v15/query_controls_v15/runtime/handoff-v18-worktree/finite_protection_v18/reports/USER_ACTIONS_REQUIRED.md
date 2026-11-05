# USER_ACTIONS_REQUIRED — v18 계획/인계

현재 추가 설치·license·논문·SPEC 파일 요청은 없다. 기존 CPU3531/3531은 모두 사용했고 새 CPU 실행은0이다. 먼저 검토할 구체적 제안은 BUDGET_PROPOSAL.json과 docs/01_IMPLEMENTATION_AND_EXPERIMENT_PLAN.ko.md다.

필요한 숫자 승인 제안: **추가 최대612회(본실험600+실패 회귀12), global CPU4143, 새 round160core-hours와1GiB**. 합산 recent8→168/v9이후19→179/global108→252core-hours, recent328→1536MiB/physical-root aggregate8→10GiB로 확대한다. 기존34GiB charged scope·최소 free10GiB·공유32slots·buildj2를 유지한다. 원래 회계 장부는 리셋하지 않는다. 이 문서는 승인서가 아니다.

미승인 상태에서 하지 않는 명령: 새 보호 producer의 build/새gem5 dispatcher. 아직 구현되지 않아 가상의 CLI명을 만들지 않았다. 승인 후 source/manifest·resource 계약과 정확성 gate를 통과시키고 동결된 실제 명령을 기록한다.

기존 실패 참조: v15 원래 early Dijkstra 종료 gate2건과 B1 post-validation seconds 누락은 v17 raw/traceback/회귀/B2 recovery로 보존돼 있다. 현재 새 실패 command는 없으며, PACKAGE_REPORT.json에 실제 ZIP 생성·검증 command와 결과를 기록한다. Gate가 실패하면 최대2회 구체적 수정 후 해당 stage를 중단하고 최소 필요한 조치를 보고한다.

승인 전 계속 가능한 일: 기존 한도 내 계획 검토·원본 SHA 검증·handoff CRC 검증. 추가 CPU가 허용되었다고 추정하거나 기존 source/config/binary를 갱신하지 않는다. TCAD/RTL/Cadence/SPICE는 이번 범위 밖이다.
