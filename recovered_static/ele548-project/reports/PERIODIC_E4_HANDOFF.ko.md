# 주기 검사 E4 인계 — 실제 PPA 미측정

기존 e4_software_interface_contract.json의 같은S*346bits/23words와 epoch·reset/refill/drain을 유지한다. Periodic method는 progress8bits를 더해 CPU65442bits이며 k32는config/synthesis constant다. 동작 및 hash는 periodic_e4_functional_handoff.json을 따른다.

제어는 prediction-read boundary의due검사, legitimate atomic update의per-word residual 유지, detector의full-history reset/130actual-commit refill/stale epoch suppression이다. Atomic callback의before residual23bits는 software transient이고 serialized RTL staging/ports/registers 비용과 FI scope는 앞으로 정해야 한다. 검사counter는 실제fault gates에 포함했지만 대표성pilot은 동일target346payload 노출로 비교했다.

현재 가정은 due-checkC1,repairR4,independent update-lane 추가response latency0이다. Multiple callbacks/same-Tick atomicity와 response serialization을 검증했으며 실제physical ports/throughput/overlap는 미측정이다. 복잡한per-word update를0cycle에 구현할 수 있다고 입증하지 않았다. 합성/면적·지연·switching power/energy 결과는 없다.

Operation counters는기존 ProtectionStats와delta_word_reads/delta_sidecar_reads/delta_parity_operations다. Zero measured radiation events/sidecars 또는missing counters를0으로 생성하지 않는다. VCD/SAIF/bit toggles로 간주하지 않는다. 실제word-by-word 논리 update와 source FIFO/rollback timing에 RTL equivalence를 확인해야 한다.

Net benefit의net/N_write 정적회계budget도JSON에 기록했다. 이는 관측trajectory를 고정한 추가cycle 여유이며 actual update-latency 손익분기점이 아니다. 실제 지연은speculation/overlap/arrival exposure까지 바꿀 수 있으므로 measured latency를gem5에 연결해 다시 평가한다. Cadence는사용자결정으로보류하고TCAD는사용하지않는다.
