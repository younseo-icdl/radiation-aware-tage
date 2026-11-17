# Qsort direction damage and bank selection

## Question and comparison

Does the large qsort response reflect broadly corrupted prediction, or a
repeat-heavy instruction stream where similar state disruption has very
different consequences? The fixed SOURCE pilot has final BPU totals and
architectural exit times. To localize a large example, reuse the separate
forced single-bit diagnostic with the same qsort binary and input. Both
fault arms inject at tick 4,310,632,751. R0 and R64 alter only the raw age
at that tick. Pinned gem5 runs at 500 ps/cycle and 1 ps/tick.

The paired aggregation checks branch identity, PC, architectural target
and outcome across clean and faulted records. It selects the two PCs with
the largest net direction damage in the earlier R0 analysis. These are
retrospective diagnostics. Harm means clean TAGE direction correct and
faulted direction wrong. Help is the reverse. Provider comparison uses
the recorded provider type, hit bank and alternate bank. The comparison
uses the faulty lookup tick to identify whether the lookup follows injection.

## Observations

| PC | Fault age | Post-injection lookups | Harm | Help | Provider tuple changes |
|---|---:|---:|---:|---:|---:|
| memcpy repeat, 0x403e16 | 0 | 2,610,313 | 304,285 | 109 | 2,050,300 |
| memcpy repeat, 0x403e16 | 64 | 2,610,313 | 77 | 116 | 9,217 |
| strcmp, 0x403d64 | 0 | 535,161 | 121,881 | 31,191 | 534,753 |
| strcmp, 0x403d64 | 64 | 535,161 | 16,545 | 16,515 | 268,168 |

No harmful or helpful direction differences occurred in the paired
pre-injection lookups at these PCs. The memcpy location accounts for
46.67% of all clean conditional trace records. Disassembly identifies the
instruction as `rep movsq`. The repeated observations include simulator
repeat control, so the observed concentration is specific to this binary,
input and simulator execution model.

At the memcpy PC, both fault arms show nonzero own-fold inconsistency and
an index or tag difference at every post-injection observation. With R0,
192,382 of its harmful predictions (63.2%) moved from a selected longest
match in bank 1 or 3 to bimodal-only. Another 49,789 harmful predictions
recorded bimodal-only on both sides. The observations support loss of useful
tagged context and changes to learned state as possible contributors.
Provider changes and learning effects can interact. The aligned CPU traces
alone do not isolate the contribution of each route.

The raw-origin tracker showed that both the active and restorable tracked
copies stayed absent from 0.284 microseconds after R0 injection and 0.131
microseconds after R64 injection, through the observed suffix. At the memcpy
PC, the last observed harmful R0 lookup was 15.635 milliseconds after
injection, close to program exit. In R64 the much smaller harmful and
helpful counts nearly cancel. Raw lifetime, fold inconsistency and net
prediction damage are distinct measurements. Total qsort runtime increased
15.72% for R0 and 0.155% for R64 in this forced diagnostic.

## Implications for the unknown workload

The fixed SOURCE results show qsort's large miss and runtime reductions
with lease4096. They do not include the per-PC fault traces needed to assign
that benefit to memcpy. The forced results explain one plausible failure
path and show why fold mismatch or clean provider frequency alone cannot
identify a bank that should receive special treatment. Even within one
workload, bank importance depends on raw age, predictor context, learning
and the instructions reached after the event.

Use full-bank lease as the primary design. The hardware needs an append
count and actual restore ownership. Its policy does not need a workload,
bank vulnerability score or knowledge of any injected event. A selective
variant may use a fixed round-robin schedule if it earns lower measured
service cost and bounds the interval between services for every bank.
Keep Hybrid05 and existing masks as prior development comparisons. An
online policy would need observable inputs, explicit coverage and measured
cost. Fold inconsistency by itself cannot establish which copy is correct
or whether a prediction will be harmed.

Freeze the policy and hardware parameters before held-out evaluation.
Choose inputs absent from policy tuning and keep their traces outside the
decision path. New fault tapes on the same qsort/Dijkstra/SHA-1 inputs
test seed generalization only. Report unseen workloads and inputs
separately and retain losses, zero-effect cases and failures. The next
physical gate is cost qualification of the workload-independent lease.

Evidence: private aligned aggregates in
`work/qsort-causal-pc-20261117-r1/PAIRED.json` and original traces and
origin logs in `work/native-cpu-pilot-20261116-r1/`. This experiment
reanalyzed existing outputs and ran zero new CPU simulations.
