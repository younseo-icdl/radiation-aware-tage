# 유한 source에 필수 보호법을 연결하기 전의 범위 계약

SOURCE FACT: 현재 [Service의 저장소](/home/youns/workspace/ele548-project-v15/query_controls_v15/src/service.hpp:70)는 raw1130bit와 path16, REC/OW fold200 및 별도 queue/stage/metadata다. [raw_bit](/home/youns/workspace/ele548-project-v15/query_controls_v15/src/service.hpp:107)는 `(head+age)%1130`으로 읽는다. 선택된 active raw130은 고정된 물리 slot130개와 같지 않다. 추가1000bit는 rollback retention이며 S*346에 포함된다고 바꿔 부르지 않는다.

SOURCE FACT: 기존 [RoundHistory](/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/role_history.hpp:21)는23개 history word에서 parity/ECC/replica를 유지하며 검출 시 selected history reset/refill130·epoch·CPU recovery protocol을 다룬다. [RoundAccess의 allocation 처리](/home/youns/workspace/ele548-project-v9/src/rate_state_v9_support/history_access.hpp:18)는 invalid bank의 allocation을 막으면서 upstream aging schedule을 유지한다. 이 기존 동작을 단순한 `if error: data=golden`으로 교체할 수 없다.

NEW DERIVATION: current physical ring1130 전체를 ECC/TMR로 보호하고 이를 기존 S*346 결과라고 표시하면 보호 범위가 달라진다. Conversely active130의 sidecar를 고정된 ring slot130개에만 붙이면 head가 이동한 뒤 selected logical scope를 보호하지 못한다. Source(raw130) 조건부 공격과 manifest 전체 WHOLE 노출도 별도다.

DESIGN HYPOTHESIS: 공통 구현에서 active raw130 register window와 retention1000을 분리하는 표현을 검토할 수 있다. 전체 raw capacity는1130으로 유지하면서, forward 시 outgoing active bit를 retention에 저장하고 undo 시 실제 retention 값을 복원한다. 모든 비교군에 같은 표현/ports를 사용해야 한다. 아직 구현하지 않았으며 기존 circular implementation을 바꾸기 전에 zero-fault prediction/training/source/rollback equality와 동일 logical-event fault differential을 통과해야 한다. Physical adjacency는 같은 layout이라는 증거가 없으므로 별도 mapping 가정이다. 기존 ring을 유지하는 다른 보호 배치도 가능하다.

필수 이식 gate는 아래와 같다. 아직 새 finite backend에서 통과한 gate가 아니다.

| 항목 | 보존할 의미 | 필요한 증거 |
|---|---|---|
| S* 범위 | raw130+path16+fold200, 같은23 word 기준 | logical word/physical cell mapping과 sidecar·replica manifest |
| P_ED frequent/periodic | parity 검출→기존 exclude/relearn·reset/refill/epoch 의미, 두 검사 정책 구별 | full vs delta 유지법을 같은 k/ports에서 분리, even-bit miss와 helper metadata 오류 |
| ECC | 실제 syndrome1-bit 정정/writeback, 2-bit DUE fallback;3+ 보장 없음 | stale repair가 newer source를 덮지 않는 version/visibility·queue·service gate |
| TMR | 실제 세 payload copy/vote/feedback; correlated copies 보장 없음 | 세 copy와 voter/update/repair ports/cost, correlated case 및 제어 storage 노출 |
| write/undo/correction | latent 오류를 새 parity/ECC로 무조건 seal하지 않기 | read-before-write/check 또는 정확한 delta 정책, consecutive RMW latest-value forwarding |
| recovery | accepted command/credit/rollback record를 잃지 않기 | 실제 drain/commit/epoch/freshness, stale restore/training, mid-repair SEU, reset 중 새 사건 |
| 비용 | syndrome/vote/maintenance/repair 작업의 실제 sampling·publication·II | 같은 logical interface와 resource 조건, 정상 유지 비용과 사건 후 비용 구별 |
| 평가 | 원래 rate/time/RNG namespace·종료 censoring 계약 | SOURCE/WHOLE 분리, 전 사건 포함, A/B/C/D와 valid paired-owner B−D/CI |

새 설계는 pending lookup과 source writes를 먼저 완료한 뒤 debt만 청구하지 않는다. Reset/relearn도 기존 speculation/commit 계약과 실제 drain/finite source 서비스를 통해 진행해야 한다. Plain/Direct에만 fast path를 주고 다른 방법의 지연을 불가피하다고 결론 내리지 않는다.

현재 v15 early prototype의 CPU-owned BI/host association은 predictor fault 범위에서 제외했고 consumer token routing/late-write port의 hardware 비용도 미검증이다. 이 범위를 명확히 닫기 전에는 WHOLE을 CPU 전체 fault coverage라고 부르거나 hardware 후보를 qualified 처리하지 않는다. 지금의 CPU18 제안은 clean cost/overlap control이며 이 보호 이식의 대체가 아니다.
