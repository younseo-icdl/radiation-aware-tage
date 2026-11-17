# Workload sensitivity and the qsort result

This analysis reuses the current clean controls and fixed SOURCE development
outputs. Committed BPU misses come from `system.cpu.branchPred.mispredicted_0::total`
in the final stats dump. Clean MPKI divides this count by committed instructions
and multiplies by 1,000. Differences below use each program's own clean native
count as the reference.

| Program | Clean MPKI | Native SOURCE extra misses, owners 0 / 1 | Lease4096 SOURCE extra misses, owners 0 / 1 | Hybrid05 SOURCE extra misses, owners 0 / 1 |
|---|---:|---:|---:|---:|
| qsort | 6.946 | 165,363 / 426,527 | 681 / 876 | 32,088 / 42,487 |
| dijkstra | 1.326 | 7,901 / 2,368 | 8 / 123 | 541 / 707 |
| SHA-1 | 0.042 | 29 / 23,307 | 0 / 164 | 29 / 19,703 |

The qsort gain coincides with a larger reduction in absolute misses. Dijkstra
applied 47 and 42 SOURCE events on the native path, compared with 33 and 43 for
qsort. Event count alone cannot explain qsort's higher damage. SHA-1 has a very
low clean miss rate and a large difference between its two owners. On owner 1,
Hybrid05 reduced misses but finished 0.029% slower than faulted native.
The instruction stream and time overlap matter, so multiplying miss counts
by a fixed penalty cannot recover task cycles. Lease4096's clean SHA-1 is
already 0.976% faster. Compare fault against clean within each method when
interpreting avoided damage.

## Where the qsort sensitivity appears

The clean committed provider mix differs across programs. Banks 1 and 3
together supply 48.68% of qsort conditional queries, 17.02% of dijkstra queries
and 34.07% of SHA-1 queries. Bank 7 alone supplies 30.13% for dijkstra.
These are frequency observations from the retained clean trace screen.
Bank use alone does not identify which bank caused a fault-induced miss.

An independent diagnostic already exists in the older forced-single-bit
screen. Reaggregate its qsort U0, R0 and R64 committed traces by PC, using
conditional rows and comparing the TAGE direction to the retired direction.
The per-PC execution counts agree across all three runs. The hottest PC,
`0x403e16`, accounts for 3,193,133 of 6,842,112 conditional trace rows (46.67%).
Disassembly places it at `rep movsq` in the binary's `memcpy` routine.
It is a modeled repeat instruction location, so these rows do not count
distinct source-level branches.

In the forced R0 run, direction mismatches at this PC grew from 177 to
304,353, an increase of 304,176 out of 483,254 net additional mismatches
(62.94%). The next-largest PC is a `strcmp` branch, with 90,690 additional
mismatches. At the same injection tick, forced R64 reduced the hottest
PC's mismatches by 39 while adding 2,098 net across all PCs. This localizes
one large diagnostic outcome and shows the importance of the injected raw
age. The older metric is the TAGE direction proxy. It does not attribute
final BPU misses in the separate fixed SOURCE batch, which retains aggregate
statistics but lacks per-PC fault traces.

## Decision for the next work

Prioritize shortening or simplifying lease service and the drain path. In the
existing qsort controls, frequent lease64 was slower than faulted native on
one owner despite full-bank reconstruction. The bank-selective lease kernel
already passes functional gates. To justify using it, compare equal service
budgets, measure actual read and write work, and use per-PC fault-added misses
and retirement timing to pick a static mask on development evidence. A mask
based only on clean provider frequency misses the distinction between a
frequently used bank and a fault-sensitive one.

The smallest diagnostic extension is a bounded final-BPU trace around
predeclared events. Record harmful and helpful outcomes by PC and provider
while preserving exact exit timing and all no-hit outcomes. Use it to test
whether fixed SOURCE damage also concentrates in the repeat-copy and string
comparison paths. Preserve the two existing candidate families and use
fresh independent owners for the final runtime evaluation.

See `source-development-2026-11-17.md` and `native-screen-2026-11-16.md` for
the two distinct study cohorts. Raw PC aggregates are preserved privately at
`work/qsort-pc-reuse-20261117-r1/`. This analysis used zero new CPU runs.
