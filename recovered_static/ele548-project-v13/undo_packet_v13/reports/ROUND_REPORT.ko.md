# v13: 긴 undo packet과 실제 source→provider stage

**IMPLEMENTED/TESTED RESULT:** 기존 v9–v12와 승인된 오류12회의 결과를 보존하고, 별도 `codex/v13-undo-packets` / `undo_packet_v13`에서 공통 source의 큰 rollback과 finite PC/provider 경계를 구현했다. 현재 gate는 C++ 기능/부품 timing 및 gem5 clock adapter object compile 범위다. **실제 O3 통합·새 CPU 결과·보호법 우위·하드웨어 qualification은 아직 아니다.** 전체 연구 목표는 active다.

## DONE — 명령 / 근거

기존 project-local Python으로 아래 명령을 실행했다. 모든 stdout/stderr/GNUtime/정확한 command·dependency SHA는 각 `runtime/<stage>/EXECUTION.json`과 `reports/*.json`에 있다. Runtime/archive는 Git에서 제외하고 별도 evidence ZIP에 보관한다.

```text
python -B undo_packet_v13/tools/gate.py service --attempt A1
python -B undo_packet_v13/tools/gate.py bulk --attempt A1
python -B undo_packet_v13/tools/gate.py tage --attempt A1
python -B undo_packet_v13/tools/gate.py bridge --attempt A1
python -B undo_packet_v13/tools/gate.py pipeline --attempt A1
python -B undo_packet_v13/tools/gate.py lookup --attempt A1
python -B undo_packet_v13/tools/gate.py lookup --attempt A2   # retained FAIL
python -B undo_packet_v13/tools/gate.py lookup --attempt A3
python -B undo_packet_v13/tools/compile_clock.py --attempt A2
python -B undo_packet_v13/tools/gate.py manifest --attempt A1
python -B undo_packet_v13/tools/gate.py serial --attempt A1
python -B undo_packet_v13/tools/audit.py --attempt A2
```

- Source gate: pinned source18,000대조, metadata4,816개 SBU, tiny-counter drain33회, 실제 operand sampling·queue-full·mid-stage SEU·accepted source 보존·ordinary recurrent update II1 통과.
- Bulk gate: 최대1000bit undo를 actual head 이동과 stage 계산으로 구현했다. 임의 raw/fold 손상을 포함한 coalesced/sequential120대조와 live operand/partial860개 SBU가 통과했다. Actual pre/post130bit latch와 actual folded200을 사용한다. Source fault를 completion 때 재읽어 몰래 복구하지 않는다.
- Native gate: synthetic60,000+기존 HW1 design trace36,000 정상과 speculative48,000/undo46,500, prediction/index/tag/provider/training/RNG·snapshot/signed-bit 통과. 공개된 design window이며 holdout/SPEC CPU application 실행이 아니다.
- Coalesced callback gate: native TAGE control160,620개, primitive undo160,860개, outer squash480개, corrected append240개를 대조했다. 중첩 begin/end와 correction append 이전 flush, 최대1000개 speculative branch를 검증했다. 동기 functional scoreboard이며 gem5 callback admission/timing backend가 아니다.
- PC/provider gate: 독립768개+실제 학습/이전 prediction·source에 의존하는 synthetic3,000개, 추가 metadata872개 SBU, stale context24개, tiny wrap33회 통과. Both-copies DUE와 illegal provider2개는 의도된 fail-closed fixture이며 성공한 faulted program으로 세지 않았다.
- Manifest gate:6개 geometry 총59,548 physical logical-bit XOR와 source snapshot 비별칭 검증. 고정된 추가 queue/latch/control을 모두 포함했다.
- Actual gem5 EventManager/EventFunctionWrapper의 새 clock object가 별도 경로에 compile됐다. 원래 binary를 재빌드/링크/실행하지 않았다. Clock은 tick0 reset부터 real event를 매 cycle 실행해 idle II/repair hold를 누락하지 않는다. BPU SimObject 등록/instantiate/link는 미구현이다.

## 동일 조건에서 single-pending과 latency를 분리한 결과

Source L은1/2, actual hash/table/provider stage는추가1cycle이다. 따라서 아래 전체 ready L은2/3이다. Source component L만 전체 predictor L이라고 부르지 않는다. RECURRENT/DIRECT/OVERWRITE 모두 동일한 결과였다. 같은 physical storage·II1·ports에서 sender의 outstanding 제한만 바꾼12개 deterministic case다.

|전체 ready L|독립128개, 여러 pending|같은128개, single pending|실제 최대 outstanding|
|---:|---:|---:|---:|
|2|129 component cycles|256 component cycles|2 vs1|
|3|130 component cycles|384 component cycles|3 vs1|

**NEW DERIVATION:** 이 독립 입력에서는 pipeline fill의 추가1cycle과 single-pending이 만들어내는 반복 대기를 구분했다. 이는 실제 프로그램 IPC 개선, 전체 LUT 지연 제거 또는 Direct 승리를 뜻하지 않는다. 입력 PC가 모두 미리 알려진 deterministic component control이며 event/owner 통계가 아니다.

500개 trained source-feedback synthetic fixture의 REC/OW는 L1/2에서1999/2998, DIRECT는1500/2000componentcycles였다. 이 fixture는 이전 응답의 실제 predicted direction으로 다음 PC를 만들고 실제 outcome은 응답 뒤 training/source update에만 사용한다. 실제 O3 fetch/ROB/BTB/memory/rollback은 모델링하지 않아 프로그램별 CPU 순위로 쓰지 않는다. REC의 현재 publication interlock에는 추가 forwarding 여지가 있으며 이를 알고리즘의 불가피한 하한으로 단정하지 않는다.

## 알고리즘과 비용의 경계

Recurrent bulk는 `ROR(actualF XOR Phi(actualBefore),n) XOR Phi(actualAfter)`를 stage에서 계산한다. Dirty discrepancy가 회전해 남으며 overwrite로 바뀌지 않았다. Overwrite는 actualAfter의 Phi를 쓰고 direct는 source만 이동한다. 원래 geometry/hash/provider/training을 바꾸지 않았다. Recurrent에는 두 Phi+rotation과 추가 latch가 필요하므로 무료로 처리하지 않는다.

Command n은10bit로 넓혔고 일반 metadata96/update-stage128payloadbit와 실제 SECDED 두 copy를 쓴다. REC update payload는476bit, 둘째 stage에는 두 Phi partial400bit를 추가한다. Ordinary job에 쓰이지 않는 배선/latch도 실제 할당된 저장소면 WHOLE component manifest에 남긴다. 추가 PC/provider4context와216bit fold/path,181bit response latch 및 metadata/control은 총2460physical bits다.

|representation|source update/query L|source bits|source+provider bits|
|---|---:|---:|---:|
|RECURRENT|1/1|7236|9696|
|RECURRENT|2/2|9010|11470|
|DIRECT|1/1|6490|8950|
|DIRECT|1/2|7044|9504|
|OVERWRITE|1/1|6890|9350|
|OVERWRITE|2/2|8118|10578|

이는 최적화하지 않은 실제 부품 storage 열거이며 면적/에너지/FIT 또는 필요한 최소 저장소가 아니다. 기존 TAGE tables·소비된 CPU BranchInfo·BTB/RAS 등은 부품 manifest 밖이다. Full predictor WHOLE manifest와 기존 SOURCE(raw130) alias를 CPU에 연결하는 작업은 남아 있다. Same-process PPA나 physical MCU 주소 대응은 주장하지 않는다.

## VERIFIED ASSUMPTIONS / 보존한 실패

Bulk coalescing은 raw buffer가 같은 atomic sampling edge에 있고 fold read/check/training이 사이에 없는 구간에만 적용한다. 실제 여러 cycle undo에 interleaved SEU를 넣은 것과 동등하다고 하지 않는다. 보호 controller의 원래 검사 schedule을 지우며 묶을 수 없다.

Raw는 register/tap interface로 pre/post window130개씩을 제공한다. One-port SRAM이라고 가정하지 않았다. Source L1/2·provider1cycle, 병렬 codec normal-stage fit은 아직 timing 가정이다. Metadata는 actual two-copy SECDED만 사용하며 총2physical flips 사이의 정정 계약을 갖는다. SECDED3+ 및 correlated multi-copy 오류를 모두 고친다는 보장은 없다. Golden/event 목록은 production port에 없다.

확장 lookup_A2는 `FAIL trained pinned provider mismatch`로 실패했다. Test fixture의 `(pc>>2)`가 standalone pinned `instShiftAmt=0`과 달랐다. 한 번의 concrete fix로 실제 parameter를 쓰도록 바꿨고 A3에서 통과했다. A2 source/binary/로그는 삭제·성공으로 대체하지 않았다. Current/historical SHA는 SOURCE_VERSION_INDEX_A2.json의 정확한 byte binding으로 확인했다.

## NOT DONE / BLOCKERS / NEXT

실제 O3 BPU request/response·연속 squash admission/backpressure·retire credit을 아직 연결하지 않았다. 기존 fetch는 pending prediction 동안 멈춰 다음 PC를 기다린다. 한 번의 긴 squash를 하나로 묶는 것과 여러 cycle squash가 큐에 몰리는 것은 다른 문제다. 무제한 host queue·payload를 버리는 cancel·계산 뒤 debt·orphan assertion을 정상 결과로 쓰지 않는다. 구체적 local source와 다음 순서는 NEXT_GEM5_CONNECTION.ko.md에 있다.

S*=346bit P0/P_ED(frequent,periodic)/ECC/TMR와 원래 NATIVE/serial 결과는 보존했다. 새 common finite source 위의 protection controller staging은 미구현이다. 보호법에 같은 forwarding/port 조건을 제공하지 않고 새 후보를 우승자로 고르지 않는다. 새로운 프로그램 cycles/IPC, A/B/C/D·B−D·paired CI, 독립 owner/입력 평가는 없다.

CPU start는 v9이전 동결 장부3009에 이번 실제 marker 확인 v9 352+v10 108+v11 clean6+fault12를 더해3487이다. 새 v12/v13 CPU0, 현재 cap3487/3487이다. 승인한12회는 이미 완료됐으므로 중복 실행하지 않았다. 새 producer/정확성/자원량이 준비되기 전 추가 CPU 수 승인을 요청하지 않는다. Compiler/license/dataset 사용자 행동은 필요 없다.

이번 recorded0.025758coreh, v12+v13 preparation0.075486/0.25, v11+v12+v13합산1.024081/2.5coreh였다. V9..v13합산12.195889/16, global77.594344/108coreh다. Package 전 다섯 worktree7.660168/8GiB, preparation36.230469/64MiB였다. 보존한 기존 charged scope20.54370880126953GiB는 과거 scope 장부이며 전체 legacy directory의 새 du가 아니다. Final package 후 값은 POST_PACKAGE_VERIFICATION.json에서 확인한다. EDA0·hardware-qualified 후보0이며 전체 목표는 active다.
