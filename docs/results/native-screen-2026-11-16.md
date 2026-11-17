# Native raw-fault development screen

Nine executions completed: three U0 controls and six UF cases. All matched expected stdout and retired instruction/PC identities; all six complete committed branch streams aligned. Every scheduled single-bit event applied once; no missing lookup or retirement joins, timeout, or failed execution occurred.

This is a forced single-event COMMON_STATE_CONDITIONAL development screen, not a radiation-rate estimate or independent evaluation. Seed 548, one raw-history XOR at one quarter of the existing clean exit tick plus one tick, two predetermined logical ages R0/R64 per program. The CPU/cache/memory and binaries/inputs are those of the current clean comparison, separate from historical B4.

| Program | Case | Cycles | Instructions | IPC | UF/U0 cost |
|---|---|---:|---:|---:|---:|
| qsort | U0 | 34,485,063 | 25,377,774 | 0.735906 | +0.000000% |
| qsort | UF-R0 | 39,906,314 | 25,377,774 | 0.635934 | +15.720577% |
| qsort | UF-R64 | 34,538,622 | 25,377,774 | 0.734765 | +0.155311% |
| dijkstra | U0 | 40,991,213 | 47,146,642 | 1.150165 | +0.000000% |
| dijkstra | UF-R0 | 41,101,698 | 47,146,642 | 1.147073 | +0.269533% |
| dijkstra | UF-R64 | 41,014,049 | 47,146,642 | 1.149524 | +0.055710% |
| sha1 | U0 | 5,905,076 | 11,608,400 | 1.965834 | +0.000000% |
| sha1 | UF-R0 | 5,979,162 | 11,608,400 | 1.941476 | +1.254616% |
| sha1 | UF-R64 | 5,905,076 | 11,608,400 | 1.965834 | +0.000000% |

Cycles are `system.cpu.numCycles` at program completion, instructions are `simInsts`, and IPC is their ratio. The exact exit-tick analysis is retained separately; the CPU cycle counter includes its initial counted cycle. U0 cycle totals match the existing current clean native results.

Raw-origin provenance disappears from active and observed restorable histories in all six UF cases. Consumed rolling folds remain inconsistent with their own source through program exit in all six: stable invariant recovery is right-censored. Equal-source reference-fold comparisons exclude divergent speculative raw/path snapshots, with alignment gaps retained. Full CPU learning/RNG-state recovery and final BPU direction/target recovery are not exported and remain NOT_OBSERVED.

The conservative timing rule uses actual retirement ticks at every conditional branch: 1024-branch windows, three full windows, epsilon zero, with finer cancellation and TAGE-direction differences excluded. All six remain right-censored under that rule. Harmful/helpful labels in the trace analysis refer to TAGE conditional direction before final BTB/target overrides, not necessarily CPU redirects. SHA-1 R64 has zero final runtime change despite TAGE-direction differences; no miss-count-to-cycle conversion is valid.

The qsort R0 penalty (+15.72%) admits one direct-query candidate with a declared additional one-cycle conditional-query latency. Its M0 and matched R0/R64 MF cases will determine whether removing persistent-fold damage pays for that model cost. Negative and zero owners remain in the comparison. The other programs do not trigger a broad candidate/rate grid. Physical area/energy/timing remain UNKNOWN.

Private artifacts: `work/native-cpu-pilot-20261116-r1/CPU_PILOT_PLAN.json`, `RUN_RESULTS.json`, `RESULTS_FINAL.json`, `RESULTS_FINAL.csv`, per-cell `native.json`, `events.csv`, `raw_origins.csv`, `committed.csv.gz`, stdout/stats/config/logs, and each UF `.analysis` directory. The first native build is `build/gem5-native-study-r1`, source commit `cb1dc2c`; the runtime factory port correction is `284440a`. The independent source tree and binary are retained.

Bounded implementation validation passed before this screen: five native cases (including duplicate-site rejection), diagnostic/future-event transparency, native completion-time equality, and all fourteen finite checksum cases. The earlier invalid interrupt responder connection failed before program execution; its logs are preserved under `work/native-study-regression-r1`, with successful revisions in r2/r3.
