# G4 정상 CPU 비용 — design-only

두 historical MiBench inputs의 정상 실행을 완료했다. Fault runs는 아직 진행 중이다. Parameter C1/R4 및 U0/U1은 actual PDK latency가 아닌 sensitivity 가정이다.

|program|P_ED/ECC/TMR C1U0|N1k64 C1U0|H1k32 C1U1|N1k64 C1U1|
|---|---:|---:|---:|---:|

모든 normal outputs/native checksum, committed instruction count가 일치했다. 최대 service debt는 qsort45/dijkstra36cycles였다.1cycle/operation을 유지하면서1boundeddescriptor에서 progress를 모델링했다. H1 또는U1의 높은clean비용은 나중failure처럼숨기거나faultbenefit만으로순위를만들지않는다. Source shadow/code/rebuild scratch/controller는manifest에실제로있다.

U0 same-stage delta logic의 physical timing·ports feasibility는 미검증이다. U1 결과를 함께 보존해 그 가정이 깨지면 이득이 사라질 수 있음을 보인다. Final holdout 선택은 실제 faultdesign결과 완료 뒤 freeze하고 새입력/owner에 적용한다.
