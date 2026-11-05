# 실제 BPU 연결에서 남은 계약

## SOURCE FACT — 고정된 local source

Pinned gem5 v25.1.0.1(c8222cc67a399bfc01e8658dd14b30d5bfd634f9)+기존 R2 patch의 `src/cpu/o3/fetch.cc:1299`는 control request가 ready가 아니면 instruction/token을 보관하고 fetch loop를 break한다. 이후 `bac->updatePC`에서 예측된 next PC를 얻는다. 따라서 finite lookup의 독립 II1을 구현해도 단일 thread의 다음 실제 branch PC/history가 곧바로 준비되는 것은 아니다. 기존 추가1cycle 결과는 기존 single-pending 구조 민감도로 유지한다.

같은 source의 `src/cpu/pred/bpred_unit.cc:406/425` simple squash와 `:468/593` corrected squash는 void/non-yielding begin/end 경계를 가진다. Corrected overload가 simple overload를 중첩 호출하고, 이후 실제 mispredicted branch의 corrected update를 호출한다. `src/cpu/pred/native_v9r2.inc:171` 이후는 finite old pipeline에 요청을 넣지만 주소는 기존 source에서 동기 capture한다. 이것이 v13의 실제 source reduction과 아직 다른 경계다. 실제 SHA는 CLOCK_COMPILE_A2.json dependency와 이전 source.lock의 transport 해시를 확인한다.

## IMPLEMENTED/TESTED RESULT

v13 Service는 한 atomic source dispatch에 최대1000bit undo를 실제 head 이동으로 처리하고, 실제 pre/post source와 stored fold를 latch한 뒤 stage에서 계산한다. 기존 ordinary recurrent forwarding/II1은 유지한다. Dirty discrepancy를 남기는 recurrent inverse jump와 overwrite Phi는 다르다. Native functional harness에서 실제 begin/end 중첩·corrected append 앞 flush가 검증됐다. 이것은 동기 scoreboard이며 timed BPU admission 구현이 아니다.

LookupPort는 finite4 context에 실제 PC/type/ID를 저장하고 Service reply의 fold/path를 실제216bit latch에 저장한다. 다음 실제 edge에 pinned hash/table/provider를 읽으며 result181bit latch에 공개한다. 독립128개 처리량과 의존 source-feedback·훈련 fixture, metadata hold/DUE/stale/wrap을 구분했다. Source L1/2+provider1이다. Source reply가 나오기 전에 provider를 계산하지 않는다. CPU-owned 소비 이후 BranchInfo는 기존 연구의 CPU 경계로 제외하되, 소비 전 추가 context/control/latch는 전부 manifest에 포함한다.

별도 gem5_overlay의 Gem5Clock은 실제 EventManager/EventFunctionWrapper에 연결되고 actual gem5 headers로 새 object가 compile됐다. Tick0 reset부터 매 CPU cycle의 real event를 수행한다. Idle II/metadata hold를 누락시키는 lazy clock/사후 debt가 아니다. 현재 BPU SimObject에 등록/instantiate/link하지 않았으며 CPU 검증이 아니다.

## NOT DONE / 구현 순서

1. BPU request/response와 실제 provider를 LookupPort에 연결한다. Admission 전에 finite context/예측 후 source write credit을 예약해야 한다. Accepted append/undo/commit은 squash로 버리지 않는다.
2. 하나의 긴 squash는 packet 하나가 됐지만, 여러 CPU cycle의 연속 squash와 corrected append가 4-entry source queue에 몰릴 때의 upstream backpressure는 아직 없다. BPU void callback에서 queue overflow 후 assertion으로 끝내거나 host vector에 무제한 저장하지 않는다. 실제 O3 squash message를 수용하기 전에 finite transaction credit을 확인하고, 거절 시 실제 PC/target/outcome/sequence를 보관해 원래 순서로 재시도하는 ownership 계약이 필요하다. 새 latch의 폭은 실제 gem5 타입/config에서 결정·manifest에 포함한다. Retired나 cancelled CPU 기록을 미래 payload의 error-free replica로 쓰지 않는다.
3. Source publication을 기다리는 recurrent query에 실제 fold forwarding을 추가할 수 있는지 별도 변형으로 검토한다. 현재 stored-fold publication 대기를 recurrent의 불가피한 최소 비용이라고 부르지 않는다. Forward할 부분과 공개되지 않은 부분의 sampling edge·protected version·SEU 노출을 분리해야 한다. Direct에만 pipeline을 주고 결론 내리지 않는다.
4. P_ED frequent/periodic·ECC·TMR의 원래 check/update/repair schedule을 새 source ownership에 연결한다. Fold-opaque interval에만 undo를 묶고 검사/훈련/복구 사이를 넘어 묶지 않는다. 아직 이 controller staging을 구현하지 않았다. 동일 S*=346 기준선·원래 native/serial 결과는 유지한다.
5. 수정된 전체 source gate→정상 native/O3 checksum·프로그램별 cycles/IPC→고정 후보/별도 owner 평가 순서다. 새로운 CPU binary와 정확성 gate·구체적 실행 수/시간/disk가 준비되기 전 실행 승인을 임의로 추정하지 않는다. 현재 actual3487/cap3487이다.

## VERIFIED ASSUMPTIONS

Raw는 register/tap interface이며 recurrent bulk에는 pre/post130bit 두 window, actualF200과 두 Phi/rotation이 필요하다. One-port SRAM을 공짜로 두 번 읽은 것이 아니다. 각 stage-fit·parallel SECDED encode/decode·table/provider1cycle은 timing model 가정이며 physical 측정이 아니다. 새로운 source+provider component bits는 full predictor/CPU storage의 최소치나 면적/에너지/FIT가 아니다.
