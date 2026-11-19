# Lease4096 rate sweep cycle and branch accounting

The 96 fresh O3 executions form 48 paired comparisons from
`work/source-rate-sweep-20261118-r2/` and `work/source-rate-sweep-20261118-r3/`.
This retrospective analysis uses their existing artifacts and the archived
clean controls. The 2,000 events/s anchor pairs are included in the handoff
for context. No simulations were added. Every fresh pair shares a logical
fault tape, fixed workload binary and input, a 13,850 ps CPU cycle, and the
same O3 settings. The lease arm requests a rebase every 4,096 raw-history
appends, waits for restore owners to drain, and charges two cycles of
service. The SOURCE rates describe accelerated raw130 injection.

## Accounting

- **Conditional misses avoided** is ordinary minus lease
  `system.cpu.branchPred.condIncorrect`. The log field `branch_misses`
  is that counter. O3 execute and commit mispredictions are separate checks.
- **Net cycles saved** is ordinary minus lease program-exit ticks divided
  by 13,850. Positive values favor lease. **Clean cost** is lease minus
  ordinary cycles in the matched zero-fault control.
- **Clean-adjusted improvement** is net cycles saved plus clean cost.
  The identity `net cycles saved = clean-adjusted improvement - clean cost`
  measures how far the faulted result moved relative to the observed
  no-fault difference. It includes fault/lease interactions and changes
  in pipeline behavior. The ratio to clean-adjusted avoided misses is
  descriptive. The aggregate counters cannot assign exact cycles to
  individual mispredictions.
- The lease trace measures **two service cycles per completed publication**.
  Failed admission checks in `native.json` split into drain and service
  wait calls. These count occasions when the fetch hook blocked admission.
  Other pipeline work can overlap them. Use the clean runtime difference
  for the observed end-to-end cost and the counters for its mechanism.
  Adding both measures would double count maintenance.

## CRC32 at 16,000 events/s

Both arms had 26,341 conditional misses in the clean control. The lease
still published 32,675 times. It spent 65,350 modeled cycles in completed
rebase service and recorded 299,836 drain waits, for 365,186 blocked fetch
checks. The clean run took 371,334 extra cycles with lease (+0.08665%).

| Seed index | Applied events, ordinary / lease | Conditional misses, ordinary → lease | Commit mispredicts avoided | Clean-adjusted cycles gained | Clean cost offset | Net cycles saved |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 95,141 / 95,146 | 57,121 → 27,068 | 29,661 | 341,800 | 92.05% | −29,534 |
| 1 | 94,917 / 94,922 | 56,014 → 27,187 | 28,457 | 327,827 | 88.28% | −43,507 |

Lease removed 30,053 and 28,827 conditional misses, respectively, leaving
both lease counts within 846 misses of the clean run. The clean-adjusted
cycle improvement was 11.37 cycles per avoided conditional miss for each
seed. With lease, 32,675/32,676 publications took 65,350/65,352
service cycles, and drain accounted for about 82% of the 365,533/365,621
blocked fetch checks. The two-cycle rebase itself was only one component
of the measured runtime burden. The adjusted gain recovered most of the
clean cost, leaving slowdowns of 0.00689% and 0.01014%.

The ordinary arm's excess conditional misses above its clean count were
30,780 and 29,673 in these sampled runs despite roughly 95,000 applied
events per arm. A shared tape gives both arms the same events while both
remain active. The longer lease runs reached five additional events per
seed before exit. Those tail counts are an outcome of the longer runtime
and therefore cannot serve as independent exposures for cycle attribution.

## Why the lower rates were enough for other workloads

Each pair below received the same number of events in both arms, except
where the applied counts are listed separately. Seed indices are zero-based.

| Workload and rate | Seed | Applied events, ordinary / lease | Conditional misses, ordinary → lease | Clean-adjusted cycles gained | Clean cost | Net cycles saved |
|---|---:|---:|---:|---:|---:|---:|
| Quicksort, 5/s | 0 | 2 / 2 | 176,655 → 176,534 | 2,944 | 37,380 | −34,436 |
| Quicksort, 5/s | 1 | 1 / 1 | 293,020 → 176,857 | 1,170,124 | 37,380 | +1,132,744 |
| Quicksort, 20/s | 0 | 10 / 10 | 303,528 → 177,192 | 1,367,030 | 37,380 | +1,329,650 |
| Quicksort, 20/s | 1 | 10 / 9 | 425,426 → 176,657 | 2,497,016 | 37,380 | +2,459,636 |
| Basicmath, 5/s | 0 | 3 / 3 | 155,061 → 141,255 | 154,350 | 32,044 | +122,306 |
| Basicmath, 5/s | 1 | 3 / 3 | 208,843 → 141,275 | 681,132 | 32,044 | +649,088 |
| Patricia, 5/s | 0 | 6 / 6 | 503,769 → 412,923 | 693,505 | 42,343 | +651,162 |
| Patricia, 5/s | 1 | 7 / 7 | 451,028 → 412,937 | 334,762 | 42,343 | +292,419 |

- Quicksort had 176,539 ordinary and 176,954 lease clean conditional misses.
  At 5/s, one seed's two events added little ordinary-arm damage. The
  other seed's single atomic two-bit event at raw logical ages R8/R9
  coincided with 116,481 extra ordinary-arm misses versus clean across
  the run. Its lease arm ended 97 misses below its own clean count. The
  first rebase publication after that event was about 1,323 CPU cycles
  later. The two 20/s pairs saved 126,336 and 248,769 conditional misses,
  comfortably exceeding the measured clean cost in cycle terms.
- Basicmath gained despite three events per arm. Lease removed 13,806
  and 67,568 conditional misses and held the totals within 37 misses of
  its own clean count. A clean-adjusted 154,350–681,132 cycle improvement
  was 4.8–21.3 times its observed clean cost.
- Patricia gained with six or seven events per arm. Lease removed 90,846
  and 38,091 conditional misses and ended within 189 misses of its own
  clean count. A clean-adjusted 334,762–693,505 cycle improvement was
  7.9–16.4 times its observed clean cost.

The discriminating factor in these samples is how much branch disruption
the matched tape produces relative to the workload's cumulative lease
cost. Conditional miss counts fell in every fresh CRC32 pair (10/10),
yet all lost time. They also fell in all fresh Quicksort, Basicmath, and
Patricia pairs (8/8 each). Their runtime wins were 7/8, 8/8, and 8/8,
respectively. Across the low-rate cases with large gains, clean-adjusted
cycle improvement was about 7.6–11.2 cycles per avoided conditional miss.
CRC32's corresponding 11.37 was comparable. The observed CRC32 loss
follows from the size of the saved-miss count relative to its larger
cumulative maintenance cost.

A separate [causal microtest](CAUSAL_MICROTEST_REPORT.md) shows that a
raw-history upset can leave a fold residual after the original bit leaves
the window. That supplies a mechanism for a few events to affect many
predictions until a rebase, consistent with the low-rate results. The
sweep records contain aggregate misprediction totals and timestamped
fault/rebase traces. They cannot identify the responsible static
branches, a vulnerable bank, or the lifetime of each residual inside a
workload. Two seeds per new point are enough to describe these observed
pairs. They do not establish a continuous crossover or a universal rate
threshold.

## Evidence and reproduction

The handoff's `data/RUN_INDEX.csv` maps every row to its archived O3
stats, native counters, termination record, applied-event CSV, shared
tape, and lease trace when enabled. `analysis/PAIR_METRICS.csv` contains
all 48 fresh pairs, six clean pairs, and 48 archived 2,000 events/s pairs.
Run `python3 analysis/analyze.py --output /tmp/lease4096-pairs.csv`
from the extracted handoff to regenerate it.
