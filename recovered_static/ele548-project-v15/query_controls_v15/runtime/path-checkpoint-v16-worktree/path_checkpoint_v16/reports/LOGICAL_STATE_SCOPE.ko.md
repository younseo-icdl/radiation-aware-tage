# v16 logical-bit scope

IMPLEMENTED/TESTED RESULT: source/provider/ingress 저장소는 `src/service.hpp::manifest`, `src/lookup_port.hpp::manifest`, `src/controller.hpp::manifest`가, early checkpoint 바인딩은 `src/early_receiver.hpp::manifest`가 정의한다. Executed protocol_A2는 REC/DIRECT/OVERWRITE × update L1/2 × query L1/2의12쌍에서 full/path 모드의 region 이름·offset·bit 폭이 모두 같음을 확인했다. Physical storage를 없애서 노출을 줄인 비교가 아니다.

기존3bit transaction kind에 ReadPath=5를 할당했다. 새 latch/queue/ID/epoch 필드는 없다. 해당 kind bit는 기존 mirrored SECDED transaction metadata에 포함된다. 현재 Source의raw1130/path16, REC/OWfold200, finite command/read/response/ACK queues, 실제1/2-stage payload와 metadata, provider context/result, ingress, 추가 early owner848bit를 그대로 노출한다. active raw130+path16+fold200의 동결 S*346과 추가 retention1000은 구분한다.

ReadPath는 source version 순서가 맞을 때 실제path16만 sampling한다. 이 명령이 fold/raw payload를 사용하지 않아도 해당 물리 latch bit를 manifest에서 제거하거나 metadata 실패를 masked로 재분류하지 않는다. 이후 full query는 정상적으로 raw/fold를 sampling한다. Fold가 손상된 상태에서 path query만 수행하면 손상은 그대로 남는다. Source stage와 provider stage의 실제 unprotected path latch SEU는 응답에 전파됨을 시험했다.

6,158개 Source/provider/ingress metadata bit와848개 early owner bit에 대한 SBU 교정은 이 유한 test fixture의 결과다. 임의 MCU 보장이나 head/FIFO/epoch의 모든 물리 결함 보장이 아니다. DUE 모호성1건은 예상한 fail-closed 예외로 검사했고, 과거 실제 simulation 실패는 보존한다. Metadata 교정에는 최소1cycle hold가 있으며 source/lookup stage도 실제로 진행한다.

ASSUMPTION/EXCLUSION: `path_only_unconditional`은 elaboration 선택 상수이며 runtime detector state가 아니다. Diagnostic counters·software clock·scoreboard·C++ host pointer/padding은 hardware injection 대상이 아니다. CPU-owned BranchInfo에 대한 host association, consumer token→record routing과 late write port의 hardware storage/비용은 기존 v15와 동일하게 제외/미검증이다. WHOLE을 CPU 전체 fault coverage라고 부르지 않는다.

이번 control은 P0-only다. P_ED frequent/periodic·SECDED·TMR의 검사/유지/복구를 생략해도 된다는 결과가 아니다. 동일 S*의 기존 필수 비교는 보존하며, 보호법을 새 유한 port에 이식할 때 원래 detector schedule과 helper storage·ports를 별도로 검증해야 한다.
