# v12 공통 finite source/service

현재 판정은 `reports/FINAL_GATES.json`과 `FINAL_REPORT.ko.md`다. 최종 producer는 **D1**이며 `SERVICE_GATE_D1.json`, `TAGE_GATE_D1.json`, `PIPELINE_BENCH.json`으로 실제 source SHA/명령/결과를 연결한다. A/B/C는 이전 단계의 동결 기록이다. 특히 C2의 L은 계산 stage 수였고 sampling1cycle이 더 들었다. D1은 준비된 요청을 accept에서 sample해 실제 request→response L1/L2를 구현한다.

`src/service.hpp`는 production 결정을 실제 저장된 data/parity/code/freshness/epoch에서만 내린다. Event list·golden model·test scoreboard는 입력이 아니다. Source와 query의 입구/계산/출구, retirement control을 분리하고 유한 queue·실제 stage·data sampling·version 보존·squash/wrap/정정 hold를 구현했다. Recurrent의 부분 결과 forwarding도 포함한다.

`tests/tage_harness.hpp`는 pinned native TAGE와 기능을 대조하는 **검증 harness**다. Source observation으로 원본 API의 helper를 유지하므로 CPU timing backend나 무료 hardware read port로 사용하지 않는다. Provider/table/PC·BPU 연결, 긴 squash의 n>2 packet service, parity/ECC/TMR controller staging과 실제 CPU 비교는 미구현이다. 기존 S*=346/P0/P_ED/P_ECC/P_TMR 비교는 보존했다.

실제로 실행한 최근 명령:

```bash
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B finite_source_v12/tools/gate.py --attempt D1
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B finite_source_v12/tools/tage_gate.py --attempt D1 --service-attempt D1
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B finite_source_v12/tools/pipeline_benchmark.py
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B finite_source_v12/tools/jump_gate.py
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B finite_source_v12/tools/closeout.py
```

이는 과거 실행 기록이다. 기존 output은 exclusive-create이며 같은 명령으로 덮어쓰거나 무단 CPU를 재실행하지 않는다. `runtime/*/EXECUTION.json`과 GNUtime이 원시 기록이다. Source/input/hash는 각 gate/plan lock에 있다. 최종 본문은 검토 과정에서 문구를 다듬을 수 있으며 수치·판정의 원본은 JSON/CSV/raw다.

`inverse_jump.hpp`는 별도 수학 prerequisite다. Atomic/static-source undo에 대한 pinned inverse와의 동일성을 증명하며 folded discrepancy를 지우지 않는다. Controller에 n1000 service를 구현한 결과가 아니다.

이번 새 CPU/EDA0, global CPU3487/3487을 유지한다. Recorded preparation0.25coreh, v11+v12합산2.5coreh/192MiB와 네 worktree8GiB·기존과금34GiB/free10GiB 상한을 함께 검사한다. 목표 전체는active이고 hardware-qualified후보0이다. 현재 사용 도구는 기존 GCC11/Python이며 새 설치/전역 설정 변경은 없다.
