# CPU4199 승인에 따른 B4 독립 평가 완료

사용자의 실제 답변 “4,199회로 확대하고 진행”을 `reports/CPU_4199_AUTHORIZATION.lock.json`에 기존4161 승인/4199제안 SHA와 연결했다. CPU 상한만38회 늘렸으며 round160coreh·namespace1GiB·shared32 등의 한도는 유지했다.

기존 coordinator는 CPU4161에서 정지했고 DEVfault102/EVALfault370이 PASS, active0이었다. 원래 coordinator를 다시 실행하지 않고 `tools/resume_eval.py`가 원래 EVAL full plan의 미시작38 SHA조건만 처리했다. 첫22+다음16병렬은1GiB 한도에서 출력 성장과 active reserve를 함께 계산한 admission이다. 기존370개 record/모든raw와 producer/config/input/seed/schedule hash를 먼저 확인했으며 B4 binary/source/기존 batch tool은 수정하지 않았다.

최종 CPU4199/4199·active0, new round107.891089/160core-hours다. B4 정상36·개발오류102·독립오류408=546건이 전부 PASS이며 B4 O3 gate18은 별도다. 이전 실패5/진단1은 원본 그대로 보존한다. 새로운668건의 raw SHA9340개와 실제 source/config/binary/입력을 검사했다. `tools/report_completed.py`는 별도 구현으로510owner행의 A/B/C/D와102summary cell을 원래 EXECUTION cycles에서 재계산했다.

완료 결과는 `runtime/continuation_b4/reports/ACTUAL_TERMINAL_AUDIT_4199.json` / `ACTUAL_TERMINAL_REPORT_4199.ko.md` / `EVAL_ANALYSIS.json` / `RESUME_4199_COMPLETED.json`이다. 이전 미완료 `ACTUAL_TERMINAL_AUDIT.json`과STOP630 및 모든 예전ZIP을 보존했다. `tools/finalize_4199.py`는 원래 audit의 출력파일명2개만 바꾼 보고용 파생이며 `FINALIZER_4199_DERIVATION.json`에 SHA로 연결한다.

분석용 compact 완료ZIP과 독립산술검증/CRC/SHA는 `handoff_analysis/20261019_completed_4199/`에 있다. 전체ELF/raw를 또 중복하는 큰ZIP의 기존disk admission 실패는 보존하고, compact 자료에는 표·보고서·provenance ref를 담는다. full raw/ELF는 원래 사용자 workspace에 남아 있다.

독립 SOURCE 평균B−D(% of finite A)는 프로그램별로 다르다:

|방법|qsort|dijkstra|SHA|
|---|---:|---:|---:|
|frequent P_ED|3.555999|1.014909|0.321092|
|periodic N1-style k64|3.548998|1.007123|0.319715|
|SECDED|3.514659|1.033741|0.408143|
|TMR|3.511400|1.033578|0.408602|
|Exact Direct|3.529358|1.034910|0.394270|

Owner8/program/scenario이며 각 방법과P0의CI를 보고 후보 간 우위를 단정하지 않는다. qsort의평균순위가개발자료와달라진점도그대로보존한다. SSTAR와WHOLE는CSV/보고서의분리된표를따른다. Native 정상보다 유한 경로 정상 비용은 여전히 크고 native matched-fault B는 없어 native 대비 절대보호순이득은 미측정이다. 공통 stage-fit 가정의 C−A=0은 물리 보호 비용0이 아니다.

현재 승인 matrix에 추가 사용자 행동은 없다. cap4199에 도달했으므로 새CPU를 더 발행하지 않는다. Native-fault 대조·정상 source/commit ordering 비용의 원인 분리 등은 다음 소프트웨어 실험 가설이며 현재 결과가 아니다. RTL/Cadence/SPICE/TCAD는 실행하지 않았다.
