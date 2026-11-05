# G2 후보와 반증 조건

G1의 100k replay에서 HF@128 뒤 잔여 net은 raw1.375/index0.167/tag0.417이었다. Raw shift-out만으로 F는 복구되지 않고, 모든 learning을 양쪽에서 동결하면 오히려 큰 피해가 남았다. 이 결과는 fixed-stream TAGE에 한정되며 CPU speculation이나 전체 workload 모집단에 대한 정량 기여율이 아니다.

N1은 update/역 update의 in/out bits로 expected parity를 유지한다. Full-word delta periodic 결과는 별도 historical control이다. Source single-bit 오류가 나중에 outgoing bit으로 전파될 때 parity가 기록하는 alarm은 full-delta와 다를 수 있으며, 성능 결과로 비교한다.

H1은 source SECDED와 folded parity를 사용한다. 안전한 CPU rebuild에는 현재 speculative raw만 보존하는 것으로 충분하지 않다. 실제 commit 순서를 받는 raw130/path16 shadow와 SECDED15bits를 추가하고 이 저장소도 fault manifest에 포함한다. 200bits rebuild accumulator와21paritybits, FSM/cursor/retry32bits도 포함한다. Shadow는 golden model이 아니며, SEU를 실제 XOR로 받는다. Source DUE는 global reset/refill로 승격한다. 이 비용 때문에 hybrid가 균일 ECC/TMR보다 불리할 수도 있다.

H_REV는 source parity/fold ECC 역할 반대 control이다. 기본 네 방법과 동일 S*를 유지한다. H2/TMR source, bank-local fallback, staged reenable, adaptive는 동시에 구현하지 않는다. 먼저 두 주 후보의 정확성·실제 CPU 비용을 측정하고 이득이 없는 복잡한 정책은 승격하지 않는다.

반증: 건강한 prediction/state/RNG 불일치; source 없는 무료 재구성; stale metadata 학습; code/replica/control 노출 누락; repair 중 fault 삭제; 프로그램 정답 오류; finite port budget 초과. 검출되지 않는 even-parity/SECDED3+는 결과에서 보존한다. Logical bits/operations/assumed latency는 PPA가 아니다.

구현/선택 규칙과 engineering performance budget은 `configs/candidate_specs.lock.json`에 동결한다. 기존 모든 holdout은 개발 맥락이다. 새 CPU 평가에는 별도 입력·owner namespace를 만들고 선택 이후 tuning하지 않는다.
