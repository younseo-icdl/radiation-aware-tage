# V10 연구 라운드 보고

이번 라운드는 기존 결과를 보존한 `/home/youns/workspace/ele548-project-v10`, branch `codex/v10-history-cost`에서 수행했다. 새 연구 charter를 운영 기준에 반영했고, 문서의 오래된 “R2 미실행” 상태를 live 완료 결과로 정정했다.

가장 중요한 관측은 **비교 경계를 바꾸면 면적의 상대 관계도 바뀐다**는 것이다. stored hash만의 기존 결과에 실제 fold 200 FF와 갱신·역복원을 포함하자, 새 mapped cell area는 recurrent 962.640µm², direct 641.466µm²였다. direct가 이 경계에서 321.174µm² 작다. 하지만 실제 source read/align/rollback ownership이 빠져 있으므로 전체 predictor 면적 우위는 아니다.

또한 기존 routed direct의 TT 지연285ps는 SS cell 조건에서379ps로 늘어났다. 가정한300ps logic budget을135개 출력 중32개가 넘었다. SS는0.81V125°C cell+기존 typical RC25°C이며 RCworst signoff가 아니다. 작은 TT 블록의15ps 여유를 전체 TAGE stage의 성공으로 해석하지 않는다.

## DONE — 실제 실행과 근거

- 같은23word/S*=346bits의 무보호·빈번parity·증분parity·SECDED·TMR primitive를 구현했다. C++/RTL64,155행과 합성 후 Q-boundary/edge/RMW64,155행이 통과했다. 실제 저장346/369/369/467/1038bits와 독립적인 검사·복제 fan-in을 감사했다.
- 실제 persistent fold200, pinned forward/inverse-undo와 direct를 공통135출력에서 비교했다. C++/RTL/mapped3,804행이 통과했다. 이전fold를 저장했다가 복구하는 다른 알고리즘으로 바꾸지 않았다.
- 일곱 production top을 같은 TT library·clock·load·입력 조건과 state 보존 원칙으로 합성했다. 별도의24FF 보존 probe를 구분해 기록했다. 새 route0이다. 면적·path class별 지연은 `COMPONENT_RESULTS.json`과 `IMPLEMENTATION_ENVELOPE.md`에 있다.
- 두 기존 routed DB의135개 출력을 TT/SS-cell, rise/fall, late/early로 모두 조회했다. 실제2160개 보고서가 존재하며 기존 DB94개 entry는 그대로다. `STA_REPORT.ko.md`에 제약·경고·누락 범위를 명시했다.
- R2의 여섯 방식162회(clean18+fault144)를 재실행하지 않고 SHA가 연결된 결과를 재사용했다. 자연 SOURCE, 강제K2, 두 WHOLE 스트레스를 분리해 선택지도를 만들었다. owner2/program으로 우위·동등성을 확정하지 않는다.
- 첫 결과 뒤 다음 설계 가설도 진행했다. lookup은 stored fold를 사용하고, update마다 원본에서 fold 전체를 덮어쓰는 소형 primitive를 구현했다. C++/RTL3,650행과 추가400 mid-cycle fold 오류 fixture가 통과했다. 아직 gem5 변형이나 새 물리 결과는 아니다.

실제 명령은 각 `runtime/*/EXECUTION.json`, `INPUTS.json`, 로그, GNUtime에 있다. 재검산 도구는 `tools/summarize_gates.py`, `component_results.py`, `mapped_state_audit.py`, `verify_preserved.py`이다. rate 분석 도구의 `--check`도 통과했다. 새 gem5 실행은0이며 global3361회 상한을 유지했다.

## 결과가 의미하는 선택

현재 SOURCE 표본에서 direct는 빈번 검사·재학습보다 qsort와 dijkstra에서 조금 느렸다. 강제K2에서는 qsort의 direct/TMR이 같았고, dijkstra에서는 SECDED가 direct보다 평균3609cycles 빨랐다. 기존 보호를 일부러 느리게 만들지 않았으며, 모두 nativeL0/stage-fit 가정을 공유한다. 프로그램별 자료와 helpful/zero/종료 후 사건을 `DESIGN_SELECTION_MAP.ko.md` 및CSV에 남겼다.

증분parity primitive는 빈번 검사형보다 RMW 경로가 짧았지만 면적은 약간 컸다. check_en0에서도 조합망이 toggle할 수 있으므로 검사 주기만으로1/k 에너지를 주장하지 않는다. SECDED의 이 구현은 setup−12ps, TMR은0ps였지만, 다른 합리적인 codeword·ports·최적화로도 반드시 추가cycle이 필요하다는 뜻은 아니다.

새 overwrite primitive는 정상 source가 주어지는 다음 update에서 이전 fold 오류를 끊었다. HOLD에서는 오류가 남고, 손상 source는 손상된 값으로 재계산했다. 따라서 source 공급, update 경로, 추가200FF 노출, speculative rollback까지 포함한 비용을 다음에 확인해야 한다.

## NOT DONE / VERIFIED ASSUMPTIONS

FULL_STAGE, source read/align/retention/rollback ownership, 전체23word 복구·refill/drain/epoch controller, 실제 finite ports/II, switching energy, RCworst/CTS/OCV/SI 및 hardware qualification은 미완료다. word-bank와 history-block 면적을 그대로 더하면 fold200을 이중 계상한다.

input50ps·slew20ps·load5fF·period500ps·output reserve100ps·setup uncertainty50ps는 비교 조건이다. SS 배선은 기존25°C typRC이다. mapped 결과는 배치 전 global interconnect estimate이다. 합성 후 오류 fixture는 Q를 edge까지 clamp하고 release한 기능 대조이며 UDP 내부 state/물리 SEU 검증이 아니다.

문헌 per-bit rate를 target FF의 mission FIT로 옮기지 않는다. 고정 창의 Poisson 발생 확률을 장기 expected runtime으로 바꾸지 않았다. 종료 뒤 피해와 반복 사건 상호작용은 여전히 UNKNOWN이다. BADGR의 direct/recurrent folding과 일관성 선행연구를 재확인했으며 최초성을 주장하지 않는다.

## 실패·blocker·NEXT

모듈명 충돌, unmapped FF preserve API, unusedQN timing query, Q_buf net-deposit fixture, 새 TB 호출의 의존파일 누락, C++ warning/parser 경계의 실패를 모두 보존했다. 수정 뒤 통과한 gate와 원시 실패를 구분했다. 실제 tool checkout에 관한 설치·license blocker는 없다.

CPU의 다음 결정은 같은 R2 native generation에서 predictor를 R1/R8 task 동안 유지할 때의 장기 피해다. 재사용 가능한 wrapper와 새 입력의 native 검증, 예산·명령은 `NEXT_NATIVE_LIFETIME_PLAN.ko.md`와 `USER_ACTIONS_REQUIRED.md`에 연결한다. 현재 global3361/3361이므로 추가 gem5는 승인된 새 숫자 상한 전까지 발행하지 않는다. 원본 direct와 conventional 비교군을 유지한 채, 다음 결과에 따라 overwrite 통합 또는 source/lookup 비용 개선을 선택한다. 검증된 hardware 후보는0개다.
