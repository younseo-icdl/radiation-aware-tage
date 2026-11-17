# Fixed SOURCE development, 2026-11-17

Three atomic-K2 implementation gates, three new lease4096 clean controls and
24 faulted CPU executions passed. All program stdout and retired architectural
PC/op identities match the native reference, instruction counts agree, BPU joins
are complete and no run exits beyond its declared tape coverage. Failures and
timeouts: zero in this batch. This is development under an assumed service model,
not an independent evaluation or a physically backannotated result.

## Frozen exposure and model

SOURCE is fixed Poisson 2000 events/s on raw130, integer K1:K2=205:9, uniformly
placed contiguous atomic XOR groups. Namespace-v2 role streams are unchanged.
For each workload, two master owners were declared before outcomes, starting at
202611170001 and adding 1,000,000 per workload and one per owner. Predictor seed
is 548. The six tapes were generated before fault runs, shared across methods,
with horizons four times the longest measured clean exit per program. No owner
was rerolled; future events and runtime-dependent applied-event counts remain.
Different elapsed runtimes may consume different prefixes of the same tape.

The three methods are original unprotected native, quiescent lease4096 with
actual owner drain and assumed two-cycle service, and static hybrid05. Extra
qsort controls are lease64, hybrid03 and hybrid60. Selection of the lease4096
cadence preceded SOURCE outcomes and was motivated by lease64's clean cost.
There are no new candidate families beyond lease and static hybrid.

CPU period is 500 ps, with the same binary/input/configuration in each program.
Hybrid has no added hash latency in this C0 model. Neither method has a qualified
full source/read/update/undo/controller PPA implementation. The B0 route results
already fail the 500 ps target for recurrent and direct blocks alike.

## Clean costs

| Program | Native cycles | Lease4096 cycles | Lease4096 vs native | Instructions |
|---|---:|---:|---:|---:|
| qsort | 34,485,063 | 34,553,752 | +0.199185% | 25,377,774 |
| dijkstra | 40,991,213 | 41,032,744 | +0.101317% | 47,146,642 |
| SHA-1 | 5,905,076 | 5,847,448 | -0.975906% | 11,608,400 |

The SHA-1 improvement is a total timing/training-visibility effect, not negative
hardware service cost. Do not subtract it as though it were a pure stall term.
Hybrid05's clean C0 cycles equal native; physical M0 cost is not established.

## Faulted comparison

Benefit is `100 * (UF_cycles - MF_cycles) / UF_cycles`; negative means slower.
All cells have matching instructions/stdout. Applied event counts are shown
because equal time exposure does not imply equal counts before termination.

| Program/owner | UF cycles/events | Lease4096 cycles/events | Benefit | Hybrid05 cycles/events | Benefit |
|---|---:|---:|---:|---:|---:|
| qsort/0 | 36,768,766 / 33 | 34,554,551 / 33 | +6.022000% | 35,491,094 / 33 | +3.474884% |
| qsort/1 | 39,361,268 / 43 | 34,596,318 / 33 | +12.105682% | 35,733,514 / 36 | +9.216558% |
| dijkstra/0 | 41,096,501 / 47 | 41,053,861 / 47 | +0.103756% | 41,002,202 / 47 | +0.229457% |
| dijkstra/1 | 41,037,184 / 42 | 41,028,883 / 42 | +0.020228% | 41,013,902 / 42 | +0.056734% |
| SHA-1/0 | 5,905,210 / 4 | 5,847,448 / 4 | +0.978153% | 5,905,210 / 4 | 0% |
| SHA-1/1 | 5,974,605 / 4 | 5,848,177 / 4 | +2.116090% | 5,976,350 / 4 | -0.029207% |

| qsort control | Owner0 cycles/events | Benefit | Owner1 cycles/events | Benefit |
|---|---:|---:|---:|---:|
| Lease64 | 37,853,224 / 33 | -2.949400% | 37,888,861 / 40 | +3.740751% |
| Hybrid03 | 36,768,766 / 33 | 0% | 36,926,905 / 39 | +6.184666% |
| Hybrid60 | 35,641,159 / 33 | +3.066752% | 37,093,746 / 39 | +5.760795% |

The qsort lease64 loss and hybrid SHA-1 loss are retained. Sparse owners and
development selection do not support population-wide superiority or confidence
interval claims. No aggregate mixes these SOURCE outcomes with the earlier
forced single-event study, B4, replay, or historical lifetime/overwrite results.
Multi-event task summaries do not establish per-event state or BPU recovery.

## Evidence and next decision

`work/integrated-source-dev-20261117-r1/` contains the pre-outcome plan, frozen
tape descriptors, atomic event logs, native summaries, exact simulator commands,
per-run records, stdout, stats, lease logs and coordinator log. Key inventories
are `SOURCE_DEV_PLAN.json`, `K2_GATES.json`, `LEASE_4096_CLEAN.json`,
`FROZEN_SOURCE_TAPES.json`, and `SOURCE_RESULTS.json`. Full native clean traces
are separately retained in `work/integrated-clean-20261117-r1/`.

Lease4096 merits measuring the actual source/read/update/undo/controller costs;
hybrid05 remains the second bounded candidate, with measured B0 physical cost
and the small SHA-1 regression retained. No independent seed batch is admitted
until those costs are backannotated and the candidate/stopping rule is frozen.
The WHOLE population is not yet complete: busy/timer/head/checkpoint and other
consumed metadata must enter a semantic union before any WHOLE coverage claim.
