# USER_ACTIONS_REQUIRED — v16

이미 제시한 v15 CPU18 budget 질문의 답변을 기다린다. 중복 질문을 보내지 않는다. 사용자 승인actual3511/cap3513의 잔여2회는 실패 회귀용이므로 새 후보 CPU로 전용할 수 없다. 원래 질문의 검토 대상은 `/home/youns/workspace/ele548-project-v15/query_controls_v15/reports/CPU18_PROPOSAL.lock.json`이며 SHA0f580dec97adc4e10466364fcaa6be2beef9336b9a96c626714a7449e5fdb191이다.

실패 command: 새 v16 C++ compile/run 실패는 없다. `python -B path_checkpoint_v16/tools/export.py`의 A1은 artifacts 디렉터리 누락, `export.py A2`는 수정 전 문서 snapshot 누락의 무결성 감사로 실패했다. EXPORT_FAILURE_A1/A2.json과 원래 source/오류 evidence를 보존했다. 두 번째 수정은 SHA가 같은 이전 문서 bytes 보존과 이후 inventory 전체 bytes 동결이다. 사용자 외부 의존성은 없다. Export A3의 실제 상태는 POST_VERIFICATION_A3.json을 확인한다. CPU command는 승인 이전에 실행하지 않았다. 두 차례 CPP compile/run 및 분석은 ROUND_REPORT의 실제 명령과 protocol_A1/A2 raw log에 기록했다. v16의 추가 CPP 대조가 통과해도 CPU 예산 승인을 대신하지 않는다.

필요 배분은 CPU cap3531, v11 이후8coreh, v9 이후19coreh, 새 CPU phase4coreh다. Global108·disk320MiB/전체8GiB·shared32slots는 유지한다. 실제 사람 reply와 proposal SHA를 v15 CPU_AUTHORIZATION.lock.json에 연결한 뒤 원래 v15 producer에서 실행한다. v16으로 후보/계획을 바꾸지 않는다.

```bash
cd /home/youns/workspace/ele548-project-v15
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B query_controls_v15/tools/run_cpu.py --run
```

추가 SPEC 설치·자료 업로드·license/PDK/Cadence 변경은 필요 없다. 승인 전에는 기존 결과 읽기·무결성 감사·C++ 자료 검토가 가능하다. v16 CPU 포팅/새 binary/paired fault campaign은 아직 준비·승인된 CPU18에 포함되지 않는다.

후속 goal 감사: `tools/block_audit.py`의 A2에서 실제 live simulation/build0, CPU3511/cap3513·예약0·승인파일 없음과 기존 SHA 보존을 재확인했다. 같은 CPU budget 답변 대기가 v15 준비→v16 C++ 대조→이번 continuation의3연속 goal turn에 존재했고, 새 CPP build도 prep238.6/240MiB에 기존2MiB reservation을 더하면 상한을 넘는다. GOAL_BLOCKED_AUDIT_A2.json에 blocked 판정과 재개 조건을 기록했다. 감사 wrapper의 A1은 작성 중인 *.time을 frozen guard가 읽어 IndexError로 실패했다. 원래 stdout/stderr/time을 보존하고, 시간 파일을 명령 종료 후 *.time으로 공개하는 wrapper 수정1회로 A2를 통과했다. Predictor/원래 guard는 수정하지 않았고 새 CPU 실패가 아니므로 예비2회를 소비하지 않았다. 이 감사 오류에 필요한 외부 dependency나 추가 사용자 조치는 없다.
