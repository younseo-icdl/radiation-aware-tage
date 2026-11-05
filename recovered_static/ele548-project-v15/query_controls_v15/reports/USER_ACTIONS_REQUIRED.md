# USER_ACTIONS_REQUIRED — v15

현재 필요한 조치: 준비된18개 새 CPU 실험의 count/time 배분 승인. 기존 사용자 승인 근거는 `/home/youns/workspace/ele548-project-v14/o3_finite_v14/reports/BUDGET_AMENDMENT_3513.lock.json` 및 최신 결정 문서다. Actual3511/cap3513에서 남은2회는 실패 회귀용이며 새 후보 실험에 사용할 수 없다.

실패한 command: 이 단계의 C++ compile/run/native/tick0 gate에 실제 실패 command는 없다. 실제 CPU command는 아직 실행하지 않았다. 실행 전 `CPU_AUTHORIZATION.lock.json`에 실제 사용자 reply와 proposal SHA를 연결해야 `tools/run_cpu.py --run`의 guard가 통과한다. 승인 이전에 `--run`을 실행해 가짜 실패 기록을 만들지 않는다.

검토 대상은 `reports/CPU18_PROPOSAL.lock.json`과 `PREPARED_REPORT.ko.md`다. 준비된18회는 backward checksum2 + synthetic overlap micro4 + candidate checksum3 + 기존 R1 프로그램9이며 모든 predictor/event 계약·input·seed548·timeout을 고정했다. 새 radiation schedule·SPEC 설치·dataset 업로드·Cadence/PDK/license 조치는 필요 없다.

요청 배분: CPU cap3531, v11 이후 recorded8coreh, v9 이후19coreh, 새 CPU 최대4coreh. Global108coreh·disk320MiB/all7roots8GiB·shared32slots는 유지한다. 새 cap은 아직 사용자 승인을 받지 않은 제안이다.

승인 후 실행할 실제 command:

```bash
cd /home/youns/workspace/ele548-project-v15
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B query_controls_v15/tools/run_cpu.py --run
```

승인 없이 가능한 검토 command는 같은 command에서 `--run`을 생략한 dry-run이다. C++/binary/manifest/source provenance 감사와 문서/로컬 commit은 계속할 수 있다. Actual CPU/E3 성능과 보호법 우위는 실행 전 미확정이다.
