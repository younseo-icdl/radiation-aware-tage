# v11 fold-overwrite 후속

별도 worktree `/home/youns/workspace/ele548-project-v11`, branch `codex/v11-overwrite`다. 원본 v9/v10 producer·실행·archive는 읽기 전용 참조이며 보존했다. 전체 연구 목표는 계속 active다. 이 round의 정확성 gate를 비용·하드웨어 우위로 승격하지 않는다.

최신 상태는 `reports/CURRENT_STATUS.ko.md`와 `CURRENT_USER_ACTIONS_REQUIRED.md`다. 승인한 오류12회는 모두 완료됐으며 `FAULT12_FINAL_GATES.json`/`FAULT12_FINAL_REPORT.ko.md`의 실제 status를 확인한다. 최신 승인은 `BUDGET_AMENDMENT_3487.lock.json`이다. `FINAL_GATES.json`/`FINAL_REPORT.ko.md`/`USER_ACTIONS_REQUIRED.md`는 정상 CPU6회가 끝난3475시점의 동결 기록이다. 이후12회의 승인·실제 실행을 이 옛 문서의 미승인 표시로 판단하지 않는다. 구현 경계는 `reports/DESIGN_AND_LIMITS.ko.md`, 처음 정한 범위는 `PLAN.ko.md`다.

## 구현과 증거

- `src/overwrite.hpp`: raw-history forward/undo 후 전체 fold overwrite. Source·golden 복구나 injector 신호는 없다.
- `src/model.hpp`, `src/correctness.cpp`: pinned plain TAGE의 전체 predictor 정상/훈련·rollback·logical-bit gate.
- `src/pilot.cpp`: 두 실제 HW1 design trace의 작은 fixed-stream 대조. SPEC CPU 실행 또는 CPU cycles 결과가 아니다.
- `src/cpu_select.hpp`, `gem5_overlay/`: 동일 알고리즘의 새 gem5 native C0 통합. finite overwrite timing은 미구현이다.
- `reports/SOURCE_A2.lock.json`, `COMPILER_DEPENDENCIES_A2.json`, `PRESERVATION.json`: 실제 원본/새 소스 SHA와 보존 판정.
- `reports/LOGICAL_STATE_MANIFEST.json`: 원본65,370 logical site+common pending152 physical bits, S*=346bit와 제외 범위. 전체 하드웨어 저장소를 포괄한다는 주장이 아니다.
- `reports/CPP_GATE.json`, `PILOT_RESULT.json`, `PILOT_SUMMARY.json`: 실제 실행·통과·raw와 연결된다.
- `reports/CPU_BUILD.lock.json`, `CPU_OVERLAY_A3.lock.json`: 실제 새 ELF와 object/library SHA, commands, include 의존성.
- `reports/CPU_REGRESSION_PLAN.lock.json`, `CPU_REGRESSION.json`: 기존 reserve6을 쓴 정상 CPU gate. 허용 상한은 전체3,475회다.

## 실행 재현 정보

사용한 공개 도구는 기존 GCC11.2.1과 기존 project-local Python이다. 새 설치·sudo·환경 전역 변경은 없다. gem5 v25.1.0.1 upstream pin은 `c8222cc67a399bfc01e8658dd14b30d5bfd634f9`이며 기존 reviewed R2 patch를 포함한다. Untouched upstream과 동일한 파일이라고 표기하지 않는다.

실제 실행했던 entry point:

```bash
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B overwrite_v11/tools/prepare_gate.py --attempt A2
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B overwrite_v11/tools/run_pilot.py --attempt A2
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B overwrite_v11/tools/build_cpu.py --attempt A3 --resume-built
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B overwrite_v11/tools/cpu_regression.py
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B overwrite_v11/tools/analyze_functional.py
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B overwrite_v11/tools/finalize.py
```

이는 **과거 실행 명령 기록**이다. 기존 output에 다시 실행하면 `open('x')`/중복 driver guard로 중단한다. 재현할 때에는 새 namespace와 별도 실행 할당이 필요하며, 보존된 원본을 지우거나 같은 output을 덮어쓰지 않는다. 실패한 A1/A2 build/gate 로그도 runtime에 남겨 두었다.

gem5는 full source/build clone 대신 원본 SCons 의존성 DB로 header consumer3개를 식별해 새로 컴파일하고, 원본1,513 object를 SHA/기존 signature 확인 후 읽기 전용으로 재사용해 새 ELF를 링크했다. 전체 original link input은1,516 object다. 원본 ELF는 재빌드하지 않았다. Exact command와 dependency는 build lock에 있고 assert는 유지했다. 새 ELF의 `--build-info`에 보이는 날짜는 재사용한 build-date object에서 온 값이며 실제 새 link 시각의 증거가 아니다. ELF SHA와 실행 기록을 사용한다.

Private 결과 package는 retained workspace에 의존하는 evidence bundle이다. gem5 ELF/object, 전체 HW1 trace·application 입력, 원문 PDF, PDK/library, 전체 environment를 포함하지 않는다. 로컬 source/bit manifest·commands·raw 로그와 SHA를 연결하며 공개 push하지 않는다.
