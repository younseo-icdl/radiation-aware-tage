# Small prediction-headroom controls

The development direct-query comparison has opposite signs at its two owners.
Before expanding methods or event rates, E5 uses four qsort executions to check
whether reducing predictor complexity is a useful direction. This is a declared
development control, not an independent evaluation or a whole-environment claim.

`simulation/gem5/configs/headroom.py --model BASE_FORCED` returns the current base
prediction after the complete ordinary TAGE query. Normal tagged reads, hashes,
upstream learning policy, allocation RNG, history updates and speculation remain.
Only the returned conditional direction is forced. Its area/energy are not those
of a minimal predictor. Its base table still follows TAGE's conditional update
policy; it is not expected to match a standalone always-trained base stream.

`--model BASE_MIN` instead instantiates `BimodalMin`: 8192 PC-indexed prediction
bits and 2048 shared hysteresis bits, with the exact original base saturation and
sharing rule. Every committed conditional branch trains that table. There is no
raw/path history, fold, tagged table, chooser, allocation RNG, or history restore
payload. A per-branch conditional marker remains for training ownership; ordinary
shared BTB, RAS and indirect prediction remain in the common CPU factory. The
model has an ordinary single base lookup/update and no extra history stage;
physical timing, energy, area and controller protection remain UNKNOWN.

The reusable bimodal component is differentially checked against upstream
TAGE's base table for 100,000 updates. Prediction and hysteresis targets are
exposed explicitly in order, for 10,240 logical bits. `--fault-tick T --fault-site
S` applies one stored bit XOR at that timestamp before the CPU tick. No raw/fold
target exists in BASE_MIN; this absence is N/A, not a zero-loss global SEU result.

Admitted cells are BASE_FORCED clean, BASE_MIN clean, BASE_MIN base-counter fault,
and U_NATIVE at the same base-counter site/tick. Select the prediction bit by the
first conditional PC in the already measured U0 trace with lookup at/after the
previously fixed quarter tick, before seeing these fault outcomes. Compare this
pair only within the new common base-counter environment; do not pool it with
the raw-only direct pilot. Counter faults are exposed, but control faults and
physical mapping are outside this partial logical experiment.

Check bounded checksum output, architectural retirement identity and fault counts
before workload use. Record completion cycles/IPC, committed conditional density,
conditional mispredictions/MPKI, CPU redirects/front-end stalls and fixed BTB/RAS
settings from stats/configs. No direction oracle or miss-penalty timing estimate
is needed. These controls can support a direction decision; they cannot replace
an independent matched-fault evaluation of the direct-query candidate.
