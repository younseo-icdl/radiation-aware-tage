# v16: unconditional path checkpoint만 읽는 C++ 대조

IMPLEMENTED/TESTED RESULT: P0 control에서 불필요한 fold 준비 대기를 제거했다. 같은 L/II·ports·유한 storage의128개 unconditional branch stream에서 REC query2/update1의 예측 완료가152→127cycles, checkpoint 완료157→131, batch retirement 완료284→258로 줄었다. Direct는127/131/258로 변하지 않았다. 이 stream에서 REC–Direct 차이는 사라졌지만 gem5 CPU 성능, 혼합 실제 프로그램, 보호법 우위는 아직 측정하지 않았다.

기존 v15 source/config/ELF/CPU18 proposal과 과거 raw 결과는 수정하지 않았다. 새 branch는 codex/v16-path-checkpoint, parent8879e43340a286225795cda258380a3c97e95ea9이며 별도 path_checkpoint_v16 namespace다. 물리 예산 중복/누락을 막기 위해 기존에 과금되는 v15 runtime 아래에 worktree를 두었다. git worktree는8개, charge하는 최상위 물리 경로는 이전과 같은7개다. 디스크/시간 ledger를 reset하지 않았다.

## 관측과 가설

SOURCE FACT: 고정한 gem5 TAGEBase::tagePredict는 unconditional일 때 table/fold lookup 없이 true를 반환한다. 근거는 `/home/youns/workspace/ele548-project-v9/third_party/gem5-native-v9r2/src/cpu/pred/tage_base.cc:374`다. 최종 target/BTB 결과에 따른 실제 predictedTaken 및 history update는 그대로 유지해야 한다. Rollback에는 해당 분기 이전의 actual path snapshot이 필요하다.

OBSERVATION: v15 early receiver는 예측 방향을 먼저 공개해도 deferred checkpoint를 위해 full source/fold read를 보냈다. REC의 fold version이 raw version보다 늦으면 이 checkpoint도 기다렸다. DESIGN HYPOTHESIS였던 “unconditional에 쓰지 않는 fold의 준비 대기가 일부 병목이다”를 별도 ReadPath로 시험했다. 새 kind=5는 기존3bit field 안에 들어간다. Actual ordered raw/path version까지는 기다리고, path16만 sampling하며 fold/raw operands와 reduction은 사용하지 않는다. 다음 conditional은 full read다.

## DONE — 실제 명령과 gate

workdir: `/home/youns/workspace/ele548-project-v15/query_controls_v15/runtime/path-checkpoint-v16-worktree`.

```bash
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B path_checkpoint_v16/tools/gate.py A1
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B path_checkpoint_v16/tools/gate.py A2
/home/youns/workspace/ele548-project-v10/.venv/bin/python -B path_checkpoint_v16/tools/analyze.py
```

A1/A2 compile/run은 모두 exit0이다. A2는 A1 통과 후 새로운 kind의 stale/fresh24조건과 source-stage path SEU 검증을 보충한 것이다. 실패를 성공으로 교체한 rerun이 아니다. 각 gate의 source bytes·dependency SHA·ELF·stdout/stderr·GNU time은 보존했다. V15 full-read source를 실행한24 timing case는 같은 새 producer의 full-read 결과와 정확히 같다. 과거 결과를 새 raw record로 복사하지 않았다. Export A1은 artifacts 디렉터리 누락으로 실패했다. 첫 수정 후 A2의 무결성 감사는 수정 전 문서의 snapshot 누락을 검출했다. 두 실패의 source/관측 transcript 또는 redirected stderr, 원래 audit/inventory를 보존했다. 두 번째 수정에서 문서의 원래 SHA와 일치하는 bytes를 복원·동결하고 이후 모든 export inventory bytes를 보존하도록 바꿨다. 새 A3 파일명으로 내보내며, 이후 실패하면 추가 수정 없이 이 export stage를 중단한다. Export 실패2건은 compile/run 실패와 구분한다.

- source-faithful native prediction/training/raw/path/nonSpecPath equality13,008 controls; nested squash720; tiny ID/epoch wrap 완료1,944; 실제 lookup outstanding 최대4.
- early checkpoint metadata848 SBU와 Source/provider/ingress metadata6,158 SBU: 실제 bit 교정 후 hold 및 정확한 owner/path 전달. Head/FIFO/order와 새 kind=5를 함께 검증했다.
- ReadPath cancel/stale/fresh24조건: source pipeline/provider latch/ready response에서 취소 후 동일 PC의 다음 epoch 응답만 전달했다.
- 유한4 context queue-full, 기존1000 source credits 고갈, claimed cancel, repair 중 재주입, source-stage 및 provider-stage path latch 오류의 실제 전파를 검증했다.
- deliberately ambiguous owner DUE1건은 expected fail-closed 예외로 확인했다. 새 실제 compile/run 실패0이며 과거 simulation 실패는 원래 producer에 남아 있다.
- full/path physical manifest12쌍 equality. 추가 storage0; 기존 owner848bit는 그대로 필요하다. 구현 범위와 제외 이유는 LOGICAL_STATE_SCOPE.ko.md에 명시했다.

## 측정 결과와 해석

아래는 U1·II1·split source/query ports, source query L 뒤 provider1edge, 같은 유한4 context 조건이다. 각 stream은128분기이고 반환된 예측과 이미 알려진 synthetic target으로 다음 PC를 정한다. 미래 actual outcome은 사용하지 않는다. Batch retirement는 stream 후 수행하므로 마지막 열을 CPU cycles나 IPC로 해석하지 않는다.

| stream | method | prediction 완료 | checkpoint 완료 | retirement 완료 | peak lookup |
|---|---|---:|---:|---:|---:|
| REC unconditional Q1 | early full |127|131|258|4|
| REC unconditional Q1 | early path |127|130|257|3|
| REC unconditional Q2 | early full |152|157|284|4|
| REC unconditional Q2 | early path |127|131|258|4|
| Direct unconditional Q2 | early full/path 각각 |127|131|258|4|
| REC conditional Q2 | plain/early full/early path 각각 |765|768|895|1|
| Direct conditional Q2 | plain/early full/early path 각각 |638|641|768|1|

Overwrite는 이 unconditional fixture에서 REC와 같았다. 모든 conditional full-vs-path timing은 변하지 않았다. 일반 stream에서 memory/table/data/next-PC dependency를 모두 제거했다는 결과가 아니다.

분리한 효과: update2/query1의 단일 실제 append 뒤 raw/path는 존재하고 fold publication만 미완료인 fixture에서 ReadPath 응답cycle2, full 응답cycle4였다. Fold가 준비되기를 기다린 차이이며 query latency나 port 개수를 줄이지 않았다. Source operand sampling/response visibility는 실제 stage에서 일어나고 precompute/debt 모델을 쓰지 않았다.

남은 효과: conditional 다음 PC는 자신의 예측 응답을 기다린다. Actual append/undo/retire ordering, query L1/2, provider1edge, finite storage·backpressure와 conservative checkpoint retirement/squash fence도 유지했다. Raw/source RMW 구현 자체의 비용과 이 대조의 CPU 이득은 미확정이다. Predictor table/lookup/training 알고리즘을 바꾸지 않았다.

오류 지속성: path-only checkpoint는 dirty recurrent folds를 고치지 않는다. 실제 fold bit를 뒤집고 ReadPath 뒤에도 손상 유지, 이후 full response에 손상된 fold가 보임을 확인했다. Program correctness나 보호 검사를 완화할 근거가 아니다.

## VERIFIED ASSUMPTIONS / 범위

S*346 P0/P_ED frequent/periodic/SECDED/TMR 및 native/기존 serial 결과는 필수 기준선으로 보존한다. 새 v16은 P0 CPP control이며 보호법 이식을 완료하지 않았다. Detector는 golden/event list를 보지 않는다. 새 source-kind metadata는 기존 보호 저장소에 포함되고 path/raw/fold 및 stage payload는 P0 semantics대로 노출한다. CPU consumer token→record routing/late checkpoint write port 비용과 CPU-owned BI fault scope는 이전 v15와 동일하게 미검증/제외다. Hardware-qualified 후보0, RTL/Cadence/SPICE/TCAD 실행0이다.

## 예산 / BLOCKERS

A2 후 actual CPU3511/cap3513, 새 v15/v16 CPU0. 남은2회는 기존 승인에서 실패 회귀용으로 지정되어 새 후보 CPU에 사용할 수 없다. 준비 합산0.120961/0.25coreh, recent3.781203/5, v9 이후14.953011/16, global80.351467/108이다. 두 CPP compile/run의 host CPU 합계약19.57초, A2 실행6.08초·peak9,432KiB, build peak259,232KiB다. 원시 time files가 기준이다. 이 수치에는 실제 기록된 timed tool 사용량을 반영하며 사람/agent 대기 wall time을 CPU에 더하지 않는다.

A2 직후 prep237.883/240MiB, recent311.715/320MiB, charged7roots7.857094/8GiB였다. 내보내기 결과는 POST_VERIFICATION_A3.json에 기록하며 실제 파일이 없으면 미완료다. 이 nested worktree도 기존 parent guard의 recursive disk/time 합산 안에 있다. 기존 binary를 다시 빌드하거나 공유 CPU job을 시작하지 않았다.

실제 blocker는 이미 제시한 CPU18 budget 질문의 미응답이다. 요청은 cap3531/recent8/v9 이후19coreh·새 CPU phase4coreh이며 아직 승인된 수치가 아니다. 기존 v15 proposal SHA0f580dec97adc4e10466364fcaa6be2beef9336b9a96c626714a7449e5fdb191을 그대로 보존한다. 이 결과로 승인 요청이나 후보를 몰래 교체하지 않는다.

## NOT DONE / NEXT

1. 실제 승인 후 원래 준비된 v15 CPU18을 수행한다: backward checksum2 → micro overlap4 → candidate checksum3 → 기존 R1 program9. 미세 stream 실제 overlap gate가 실패하면 early workload를 dispatch하지 않는다. 재현/개발 자료이며 독립 holdout이나 ABCD fault comparison이 아니다.
2. v16 path-only의 CPU 포팅/새 ELF는 별도 변경·gate·예산 계획으로 결정한다. 아직 실행하지 않았다. V15의 full checkpoint CPU control과 섞지 않는다.
3. 동일 source/ports의 보호 controller 이식과 consumer routing/late-write 자원 범위를 닫은 뒤 SOURCE(raw130)/WHOLE·기존 event rate/time/RNG/censoring의 paired-owner A/B/C/D 평가를 별도로 고정한다. 선택 seed와 평가 seed는 분리한다.

이번 결과의 next decision은 “unconditional 경로에 fold 준비를 요구할 이유가 없다”는 P0 구조적 대조를 유지하고, CPU가 그 요청 중첩을 실제로 활용하는지 먼저 확인하는 것이다. Direct나 새 방법이 최종 승자라는 결론은 없다. 전체 연구 goal은 active다.
