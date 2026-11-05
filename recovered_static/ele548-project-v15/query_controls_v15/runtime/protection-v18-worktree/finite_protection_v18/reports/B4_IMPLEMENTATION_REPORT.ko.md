# B4 finite protection — 정확성 gate와 현재 실행

DONE: B3 반복 SOURCE qsort ECC의 DUE/reset 이후 ingress-credit 실패를 원본으로 보존했다. `runtime/commit_ingress_repro_B3_run/EXECUTION.json`은 같은 production SourceAccess의 delayed8/overflow4 반례다. 실제 O3 내부 queue/prepared 조건의 미관측 범위는 B3_B4_ADMISSION_CAUSAL_SCOPE.ko.md에 명시했다.

DONE: 별도 producer_source/B4와 gem5_build_B4_C1 ELF에서 actual architectural retirement의 resolved outcome를 같은 callback으로 등록하고, 보호된 commit-used bit로 one-write/cycle을 지킨다. 늦은 BPU training은 재등록하지 않는다. 기본 TAGE history/hash/provider/training과 lookup/RMW L/II·queue·ports는 유지했다. 수정된 commit bridge를 실제로 사용하도록 새 commit.o까지 재컴파일했다. 기존 source/config/ELF/raw·실패·입력·owner·schedule은 바꾸지 않았다. 첫 B4 build의 absolute include 오류와 C1 수정·로그는 보존했다.

DONE: `tools/rebuild_b4_c1.py`의 C++8gate, 추가64retire/105backpressure·metadata112SBU, pre-reset 지연 training/예약 squash/used-port112SBU 시험이 통과했다. `continuation_b4/tools/initialize_b4.py`의 6방법 tick0 manifest와 `gate_b4.py`의 실제 O3 checksum6·overlap6·mid-DUE6이 PASS다. 실제 ECC DUE1/reset1/committed publication133/drain1을 관측했다. Raw/log/argv·source/config/ELF SHA는 개별 report/EXECUTION에 있다. B4_CORRECTNESS_ACCEPTANCE와 B4_SOURCE_AND_LOGICAL_MANIFEST.lock이 범위를 묶는다.

DONE: Actual L1 populations P0 77627/parity77673/ECC77869/TMR79011/Direct76611·semanticunion79429를 bijection으로 확인했다. Commit-used payload1bit/encoded2bits를 모든 WHOLE에 포함한다. Added sidecars/replicas는 source와 registered stage를 함께 포함하여 P0 대비 parity46/ECC242/TMR1384bits다. 이는 선언된 logical storage이고 실제 RTL PPA가 아니다.

NOT DONE: 새 B4 fresh normal18·개발fault102·독립normal18/fault408 전체는 아직 완료되지 않았다. 현재 정상 pilot2가 실제 통과했고 나머지16을 병렬로 진행한다. 이전 B3 정상18/native6·B2 serial18/L2six는 각각 원래 producer의 참고 측정으로 남기고 새 B4 실행으로 복사하지 않는다. B3 ECC pilot 실패를 B4 성공으로 바꾸지 않는다. 새로운 hardware winner/area/energy/mission FIT 결과는 없다.

VERIFIED ASSUMPTIONS: source register/RMW와 check/encode/provider stage-fit·23lane vector·TMR bank access·metadata correction clock은 유한 CPU resource 모델 가정이다. SOURCE raw130 조건부 사건과 WHOLE 노출은 분리하고 기존 RNGv2/time/K/rate/censoring을 유지한다. Newstorage 때문에 WHOLE population만 실제 manifest에 맞춘다. 실제 retired outcome를 사용하며 미래 branch/golden/injector list는 production control에 주지 않는다. Provider/table LUT1은 고정이므로 source L1/L2와 LUT 자체 지연을 혼동하지 않는다. Stall 합계를 정확한 CPI 인과 분해로 쓰지 않는다. Primary B−D는 공통 finite P0 기준이며 original native matched-fault B는 없다. 정상 C−A가 작아도 P0에 공통 slot 비용이 있어 실제 ECC/TMR 비용0을 뜻하지 않는다.

BLOCKERS: 현재 승인4161/round160coreh·모든disk·shared32 안에서 진행 중이다. Full B4 plan은 기존104+B4gate18+remaining546=668new/global4199이므로 CPU38회만 별도 질문했다. 아직 실제4199 승인이 없으며 현재 한도를 지킨다. 시간/disk 확대나 설치/license/PDK/SPEC/논문 업로드는 지금 요청하지 않는다. RTL/Cadence/SPICE/TCAD는 진행하지 않는다.

NEXT: B4 freshnormal18와 실제 값·RNG equality → 고정 SOURCE pilot2를 포함한 개발102 → 후보/resource/owner 고정 → 새 입력/독립owner8의 normal18/fault408. gate/pilot 후 최대32 sharedslots를 사용한다. coordinator와 source/config/binary를 중복 실행·수정하지 않는다. `continuation_b4/tools/status_b4.py`로 확인한다. B4 watcher는 현재 coordinator 종료와 모든 raw 종료를 확인한 뒤 실제 terminal audit와 새 ZIP을 만든다. 실패/예산 정지면 미완료·실제 실패를 보존한다. 인계 ZIP `BP_SEU_Finite_Protection_B4_Gates_Continuation.zip`은 source/gate18 overlay이며 전체 ABCD 결과나 ELF 배포본이 아니다.
