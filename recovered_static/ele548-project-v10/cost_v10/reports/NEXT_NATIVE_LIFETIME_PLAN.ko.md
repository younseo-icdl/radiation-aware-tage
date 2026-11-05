# 다음 native retained-state 대조: 실제 준비 상태

**PREPARED_PLAN_NOT_EXECUTABLE:** 기존 same-process 반복 workload의 새 R2 입력 검증6회는 실제 PASS다. 그러나 새 namespace의 dispatcher/단계별 lock은 아직 없고, global CPU3361/3361로 잔여 trial이0이다. gem5를 시작하지 않았다. 기존 R2 dispatcher는 ROOT/OUT이 과거 namespace에 고정되어 있으므로 그대로 실행하면 안 된다.

주 계획은 구현된 반복 wrapper를 재사용하는 **실측108회+reserve6=최대114회**다. 별도의 task-marker72안은 설계 구상이며 현재 계획을 대체하지 않는다.

## 실제로 완료한 준비

원본 `rate_state_v5/runtime/configs/persistent_inputs.lock.json`은3개 공개 프로그램의 동일 process R1/2/8/32 반복 wrapper와 native 정답 검증을 기록한다. 원본의 wrapper는 `R /absolute/input/path` 두 항을 control 파일에서 읽고 `v5_task(2,args)`를 R번 호출한다. 입력 파일 close와 성공한 dijkstra `exit(0)`→return 외 기존 kernel을 유지한 공개 소스 파생물이다. 원래 binary3개의 SHA를 확인했다.

이번에는 기존 binary를 그대로 실행하면서 현재 R2 입력을 가리키는 control6개를 새 `cost_v10/next_lifetime_prepare/cases/`에 만들었다.

|프로그램|R1|R8|검증|
|---|---|---|---|
|qsort_small|PASS|PASS|stdout가 R2 native 정답×R와 byte 일치|
|dijkstra_small|PASS|PASS|동일|
|sha1|PASS|PASS|동일|

여섯 실행 모두 exit0·stderr0이며 원본 binary/input/정답 SHA는 실행 전후 동일하다. 각 명령은 GNU `time -v`로 기록했다. 증거는 `next_lifetime_prepare/NATIVE_PREPARATION.json`, `PREPARE_NATIVE.log/.time`, 각 case의 `NATIVE_EXECUTION.json`, `native.stdout/.stderr/.time`이다. 전체 준비 helper의 실제 user0.05s/system0.00s이며 자식 실행 시간은 여기에 포함된다. 자식 `.time`과 outer `.time`을 중복 합산하지 않는다. 새 compile·gem5·EDA는0이다.

기존 R2 source/binary/config와 조건부 single-SBU 코드를 읽어 지원 여부도 확인했다. `native_v9_campaign.py`는 tick을 `integers(1,A*500+1)`, raw age를 별도 location RNG의 `integers(130)`에서 뽑는 single-SBU를 이미 사용한다. R2 predictor는 `tick logical-ID` 형식의 flat schedule을 그대로 지원한다. 새 보호 구조나 fault hook을 만들 필요가 없다.

## 질문과 비교 계약

경쟁 설명은 다음 둘이다.

1. 순환 history/학습 오염의 누적 피해가 native R2에서도 반복 task에 남고 direct가 이를 줄인다.
2. 기존 parity 재학습·정정도 같은 누적 피해를 충분히 줄이며, 과거의 장기 차이는 resource/timing/구현 세대 또는 cache/allocator/wrapper 조건에 의존한다.

세 프로그램 모두와 고정 여섯 방식을 유지한다: U, frequent parity+재학습, periodic incremental parity k64+재학습, SECDED, TMR, exact direct. R1과 R8 각각 자기 clean 대비 추가 cycles/misses와 공통 U 대비 B−D를 계산한다. 단일 process의 반복 사이에 BPU·CPU/cache·allocator를 reset하지 않는다. warm 상태는 함께 유지되므로 predictor-only 유지기간의 인과 효과라고 주장하지 않는다. 기존 입력을 이미 본 뒤의 기작 진단이며 새 프로그램/SPEC score/독립 confirmation이 아니다.

프로그램당 새 owner2개는 통계 power를 보장하기 위한 n이 아니다. 두 time/site 사건에서 R1/R8 누적 응답과 방법 간 차이가 재현되는지 관찰하기 위한 고정된 소규모 진단이다. task8개와 여섯 policy replay를 독립 표본으로 늘리지 않는다. 프로그램당 두 owner의 matched signed 결과와 min/max를 주로 보고하며 모집단 우위·동등성·tail 안전성을 선언하지 않는다.

## 고정한 fault/RNG/time 의미

- 사건은 **조건부 SOURCE raw130 SBU 정확히1개**다. Poisson2000events/s나 CHARM multiplicity 실험이 아니다. 따라서 사건율을 정의하거나 E[K]로 변환하지 않는다.
- tick은 새 wrapper의 U/R1 clean 실제 cycles H에 대해1..H×500에서 균일 추첨하고, 위치는 실제 raw130 site IDs65024..65153에서 균일 추첨한다. H에 기존 standalone R2 cycles를 대입하지 않는다.
- 2GHz/500ticks-per-cycle와 namespace v2의 time/location 분리를 유지한다. master11617480000+program_index×1000000+owner_index를 사전 선언했다. 알려진69개 기존 config JSON에서 literal 충돌은 없었고, 최종 freeze 전에 전체 registry를 다시 확인해야 한다.
- 같은 owner의 시간·site를 R1/R8 및 여섯 방식에 재사용한다. 독립 표본은 프로그램/owner tuple6개다. 같은 사건의 반복 replay는 새 입자가 아니다.
- 새 fault tape는 아직 생성하지 않았다. 미래 사건·no-applied·helpful·zero-impact를 유지하고, 정답·damage·K 결과를 보고 다시 뽑지 않는다. event는 실제 종료 tick 이하일 때만 적용한다.
- 첫 R1 clean 참조창이지 R8의 실제 첫 task 경계로 계측된 창은 아니다. wrapper에는 task marker가 없으므로 이 한계를 명시한다.
- locked interpreter는 `/home/youns/workspace/ele548-project-v10/.venv/bin/python`, NumPy2.5.4다. root가 실제 probe로 확인한 기존 환경이며 설치는 필요 없다. PATH `python3`의 NumPy2.4.4로 event tape를 만들지 않는다.

이 SOURCE 진단은 고정 S* 전체나 added-storage WHOLE을 다시 시험하지 않는다. 기존 R2 K2/WHOLE 결과는 별도 evidence로 보존한다. 추가 storage나 metadata 실패를 무영향으로 바꾸거나 direct를 ECC-free라고 부르지 않는다.

## 고유 CPU 횟수와 gate

|서로 겹치지 않는 발행 묶음|회수|
|---|---:|
|qsort R1 정상 all6 gate|6|
|나머지 정상 clean|30|
|qsort R1 owner0 single-SBU all6 gate|6|
|나머지 fault|66|
|실패 원인·회귀용 reserve|6|
|최대 새 CPU|114|

즉 본 실험은 clean36+fault72=108이고, gate12개는 이108 안에 이미 포함된다. gate를 다시 더하지 않는다. reserve는 harmless/helpful 결과를 다시 뽑거나 실패를 대체하는 데 쓰지 않는다. 실패 원자료와 null cycles를 남기며, 한 stage의 concrete fix는 최대2회다.

새 dispatcher는 먼저 정상 qsort R1의 초기2개를 검증하고 all6 정상 gate를 통과한다. R8 clean의 qsort/dijkstra U 두 case도 기존 clean36 안에서 먼저 측정하여 길어진 실행의 시간·디스크를 확인한다. 모든 clean 결과가 올바르고 정상 동등성·state/RNG 조건을 충족한 뒤에만 H와6개 owner schedule을 freeze한다. 그 뒤 첫 single-SBU all6 gate를 통과하고 남은 fault를 발행한다. initial2, 이후 최대32개의 공유 lease를 사용한다. 새 gem5 source/binary/config가 바뀌지 않으므로 unrelated metadata CPU13회는 반복하지 않고 바뀐 workload/runner/schedule을 검증한다.

## 어떤 계측이 실제로 가능한가

기존 producer/config는 종료 시 cycles·instructions·IPC·committed conditional/all-branch mispredictions, event XOR·applied/future·repair, 최종 semantic-base/RNG hash 및 raw/fold 관계 검사값을 낸다. 이는 R1/R8 **누적 endpoint 응답**을 측정할 수 있다.

현재 없는 것은 task별 boundary tick/추가 cycles/misses, component raw/fold/table bit discrepancy snapshot, R8 이후 tail이다. `dumpSeu()`는 `PROGRAM_END/RIGHT_CENSOR_MARKER`를 추가하므로 중간 snapshot으로 호출하면 안 된다. frozen config는 fault schedule에 `--audit`를 허용하지 않으므로 이를 우회하지 않는다. R8−R1도 서로 다른 R control/prologue/branch stream의 차이를 포함하므로 정확한 후기 task 피해 적분이라고 부르지 않는다. 끝까지 남는 피해는 right-censored UNKNOWN이며, 종료 값0도 이후 tail0의 보장이 아니다.

따라서 이 최소 대조는 과거 자료에만 있던 **native R2의 유지창별 누적 피해**를 채운다. 완전한 task별 damage kernel을 채웠다고 발표하지 않는다. task별 kernel이 다음 설계 선택에 꼭 필요하면 아래의 별도 marker 프로토콜을 구현·검증해야 한다.

## 실행시간·디스크 제안 — 새 pilot 실측이 아니다

실제 R2 162회의 host CPU는1.888067core-hours였다. 프로그램별 평균은 qsort 36.5233초, dijkstra 74.9676초, sha1 14.3802초다. 다음 수치는 **새 R8 실행속도를 측정한 값이 아니다.** R8 host 비용이 한 task의8배라는 선형 가정에0.75..1.5배 미측정 계수를 준 예상이다.

- 본 실험108회 선형 예상5.6642core-hours.
- reserve6개를 모두 가장 느린 dijkstra R8으로 계산하면0.999568core-hours.
- 합계 중심값6.663768, 가정 범위 약5.0..10.0core-hours.

R8 warm cache/allocator와 wrapper·입력 차이가 있어 이 범위는 보장이 아니다. 포함된 초기 R8 측정 뒤 남은 전체 batch를 재추정하고, actual10core-hours를 넘기지 않도록 발행을 막아야 한다. 부족하면 기존 작업을 건드리지 않고 원자료·잔여수·수정한 예상을 보고한다.

제안할 변경은 **CPU3361→3475**, **v9+v10 recorded12→16core-hours**다. 새 후속 CPU round cap은10core-hours이며 root의 현재 기록5.626과 합하면15.626으로16 이내다. global108core-hours는 유지한다. 완료한 `cost_v10` component round의2core-hour cap을 소급 변경하는 것이 아니다.

출력은 기존 R2가 아닌 새 `/home/youns/workspace/ele548-project-v10/native_lifetime_next/runtime`에 둔다. completed component namespace의512MiB는 유지하고, 후속 namespace cap384MiB, v9+v10 worktree 합계8GiB·누적34GiB·free10GiB·공유32lease도 유지한다. 실제 R2 raw report91.742MiB/162회에 R 길이 계수를 적용한 예상이며, 새 R8 case 크기를 먼저 측정한다. 필요 없는 대형 audit/read log를 켜지 않고 새 gem5 source/build나 proprietary model/DB를 복사하지 않는다.

## 아직 없는 실행 코드와 다음 안전한 동작

새 runner 예정 경로는 `cost_v10/next_lifetime_prepare/native_lifetime_runner.py`이며 **현재 존재하지 않는다**. 필요한 최소 작업은 다음과 같다.

1. 기존 R2 binary/config를 absolute read-only 경로로 고정하고, 위 새 output prefix만 쓰는 runner를 작성한다. 기존 `native_v9r2_eval.py`, `native_v9_common.py`, `v3_cpu_common.py`의 ROOT/OUT을 그대로 실행하거나 원본을 수정하지 않는다.
2. 실제 native-검증 control/expected stdout을 사용한 clean36개와 policy/argument/hash lock을 생성한다. plan JSON의36개 clean template이 구체적인 기준이다.
3. 새 clean H 후6개 owner tape와 fault72개를 immutable freeze하고, actual run marker/GNUtime/slot/core-hour/disk/censor/정답/conservation 검사를 붙인다.
4. root가 policy/hash gates 및 승인 파일을 확인한 뒤에만 발행한다. 현재 존재하는 실행 명령으로 가장하지 않는다.

지금 안전하게 실행할 수 있는 명령은 JSON 문법 검사뿐이다.

```sh
python3 -m json.tool cost_v10/configs/NEXT_NATIVE_LIFETIME_BATCH.json >/dev/null
```

추가 m5-marker72안은 local source의 `m5_work_begin/end`, `System.exit_on_work_items`, workbegin/workend exit와 workid 반환이 존재함을 읽어 확인한 설계다. 새 marked wrapper/native-stub·workitem simulate loop·cumulative stats parser·normal/fault observation ON/OFF gate가 아직 없다. 이 안을 현재114회 계획의 실행 가능한 대체물로 제시하지 않는다. 새로운 major predictor 후보는 어느 안에도 없다.

DONE: 실제 native6 PASS 및 원본 불변·108/114 concrete plan·RNG/단위·부족한 계측·예상·필요 승인 분리. NOT DONE: 새 dispatcher/config-phase locks·새 fault tape·새 CPU 실행·task별 kernel. BLOCKERS: runner 미구현, 잔여 CPU0, 새 시간/CPU cap 미승인. 다음 권한 질문은 root가 준비 상태를 보고한 뒤 필요한 범위에 한해 한다.
