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

## Direction accuracy and program completion

The simulator's TAGE provider counters score the saved direction prediction
(`tagePred`) against the actual direction (`taken`) at committed conditional
branch update. Sum the Correct and Wrong counters across the four providers
(longest, alternate, bimodal alternate, and bimodal). The sum equals both
the native conditional update count and gem5's committed conditional
branch count in all 204 executions. Each pair has identical instruction
and committed conditional counts.

- **Direction accuracy (%)** is 100 × Correct / (Correct + Wrong).
- **Direction MPKI** is 1,000 × Wrong / retired architectural instructions.
  This denominator agrees with gem5 `simInsts`. The handoff also has
  separate BPU and O3 commit MPKI columns.
- **Completion** uses program-exit ticks. Divide by 13,850 for CPU cycles
  or by 10¹² for simulated seconds. Percentage benefit is 100 × (ordinary
  cycles − lease cycles) / ordinary cycles.

Lease improved direction accuracy in **46 of 48** fresh pairs. SHA-1 at
20 events/s seed 1 tied with zero applied events. Dijkstra at 20 events/s
seed 0 was lower by 0.00223 percentage points. The largest observed
clean-to-faulted accuracy loss for each design, using that design's clean
reference, was as follows. The two maxima can occur on different tapes.

| Workload | Fresh pairs improved / tied / worsened | Ordinary clean accuracy | Lease clean accuracy | Worst ordinary loss (pp) | Worst lease loss (pp) |
|---|---:|---:|---:|---:|---:|
| Quicksort | 8 / 0 / 0 | 97.42300 | 97.41689 | 11.51669 | 0.59445 |
| Dijkstra | 7 / 0 / 1 | 99.41421 | 99.41421 | 0.36141 | 0.02483 |
| SHA-1 | 5 / 1 / 0 | 99.95466 | 99.95466 | 3.72184 | 1.20100 |
| Basicmath | 8 / 0 / 0 | 99.26023 | 99.26023 | 4.45541 | 0.62545 |
| Patricia | 8 / 0 / 0 | 99.36469 | 99.36469 | 5.72212 | 0.58102 |
| CRC32 | 10 / 0 / 0 | 99.96726 | 99.96726 | 0.03859 | 0.00106 |

Selected sampled points below show ordinary → lease for both seeds.
CRC32 illustrates why completion is a separate endpoint. At 16,000
events/s lease direction accuracy stayed within 0.00106 percentage
points of its clean value and direction MPKI nearly halved, while
completion took slightly longer.

| Workload | Events/s | Seed | Direction accuracy (%) | Direction MPKI | gem5 completion cycles | Runtime benefit |
|---|---:|---:|---:|---:|---:|---:|
| Quicksort | 5 | 0 | 97.42123 → 97.42319 | 6.95262 → 6.94734 | 32,437,647 → 32,472,083 | -0.10616% |
| Quicksort | 5 | 1 | 95.72056 → 97.41834 | 11.53781 → 6.96042 | 33,608,421 → 32,475,677 | +3.37042% |
| Quicksort | 20 | 0 | 95.70942 → 97.41355 | 11.56784 → 6.97335 | 33,808,394 → 32,478,744 | +3.93290% |
| Quicksort | 20 | 1 | 93.78427 → 97.42138 | 16.75825 → 6.95223 | 34,931,013 → 32,471,377 | +7.04141% |
| Dijkstra | 200 | 0 | 99.32536 → 99.41241 | 1.30472 → 1.13637 | 39,833,752 → 39,801,359 | +0.08132% |
| Dijkstra | 200 | 1 | 99.32439 → 99.41369 | 1.30658 → 1.13389 | 39,835,362 → 39,799,386 | +0.09031% |
| SHA-1 | 20 | 0 | 99.51462 → 99.93862 | 0.33105 → 0.04187 | 6,359,469 → 6,317,536 | +0.65938% |
| SHA-1 | 20 | 1 | 99.95466 → 99.95466 | 0.03093 → 0.03093 | 6,318,321 → 6,316,746 | +0.02493% |
| Basicmath | 5 | 0 | 99.07536 → 99.26002 | 1.35393 → 1.08353 | 57,794,284 → 57,671,978 | +0.21162% |
| Basicmath | 5 | 1 | 98.35663 → 99.25971 | 2.40635 → 1.08398 | 58,321,140 → 57,672,052 | +1.11295% |
| Patricia | 5 | 0 | 98.54348 → 99.36302 | 2.24779 → 0.98303 | 85,814,302 → 85,163,140 | +0.75880% |
| Patricia | 5 | 1 | 99.00777 → 99.36296 | 1.53127 → 0.98312 | 85,460,415 → 85,167,996 | +0.34217% |
| CRC32 | 0 | 0 | 99.96726 → 99.96726 | 0.05162 → 0.05162 | 428,544,397 → 428,915,731 | -0.08665% |
| CRC32 | 16,000 | 0 | 99.92866 → 99.96634 | 0.11246 → 0.05307 | 428,894,410 → 428,923,944 | -0.00689% |
| CRC32 | 16,000 | 1 | 99.93008 → 99.96620 | 0.11024 → 0.05329 | 428,881,673 → 428,925,180 | -0.01014% |

## Cycle accounting and BPU miss counts

- **BPU misses avoided** is ordinary minus lease
  `system.cpu.branchPred.condIncorrect`. Despite its name, both sweep
  producers increment it for every committed mispredicted branch tracked
  by the BPU. It equals `mispredicted_0::total` and includes target and
  non-conditional misses. The run field `branch_misses` is this counter.
  O3 execute and commit mispredictions are separate checks.
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

Both arms had 26,341 BPU misses in the clean control. The lease
still published 32,675 times. It spent 65,350 modeled cycles in completed
rebase service and recorded 299,836 drain waits, for 365,186 blocked fetch
checks. The clean run took 371,334 extra cycles with lease (+0.08665%).

| Seed index | Applied events, ordinary / lease | BPU misses, ordinary → lease | Commit mispredicts avoided | Clean-adjusted cycles gained | Clean cost offset | Net cycles saved |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 95,141 / 95,146 | 57,121 → 27,068 | 29,661 | 341,800 | 92.05% | −29,534 |
| 1 | 94,917 / 94,922 | 56,014 → 27,187 | 28,457 | 327,827 | 88.28% | −43,507 |

Lease removed 30,053 and 28,827 BPU misses, respectively, leaving
both lease counts within 846 misses of the clean run. The clean-adjusted
cycle improvement was 11.37 cycles per avoided BPU miss for each
seed. With lease, 32,675/32,676 publications took 65,350/65,352
service cycles, and drain accounted for about 82% of the 365,533/365,621
blocked fetch checks. The two-cycle rebase itself was only one component
of the measured runtime burden. The adjusted gain recovered most of the
clean cost, leaving slowdowns of 0.00689% and 0.01014%.

The ordinary arm's excess BPU misses above its clean count were
30,780 and 29,673 in these sampled runs despite roughly 95,000 applied
events per arm. A shared tape gives both arms the same events while both
remain active. The longer lease runs reached five additional events per
seed before exit. Those tail counts are an outcome of the longer runtime
and therefore cannot serve as independent exposures for cycle attribution.

## Why the lower rates were enough for other workloads

Each pair below received the same number of events in both arms, except
where the applied counts are listed separately. Seed indices are zero-based.

| Workload and rate | Seed | Applied events, ordinary / lease | BPU misses, ordinary → lease | Clean-adjusted cycles gained | Clean cost | Net cycles saved |
|---|---:|---:|---:|---:|---:|---:|
| Quicksort, 5/s | 0 | 2 / 2 | 176,655 → 176,534 | 2,944 | 37,380 | −34,436 |
| Quicksort, 5/s | 1 | 1 / 1 | 293,020 → 176,857 | 1,170,124 | 37,380 | +1,132,744 |
| Quicksort, 20/s | 0 | 10 / 10 | 303,528 → 177,192 | 1,367,030 | 37,380 | +1,329,650 |
| Quicksort, 20/s | 1 | 10 / 9 | 425,426 → 176,657 | 2,497,016 | 37,380 | +2,459,636 |
| Basicmath, 5/s | 0 | 3 / 3 | 155,061 → 141,255 | 154,350 | 32,044 | +122,306 |
| Basicmath, 5/s | 1 | 3 / 3 | 208,843 → 141,275 | 681,132 | 32,044 | +649,088 |
| Patricia, 5/s | 0 | 6 / 6 | 503,769 → 412,923 | 693,505 | 42,343 | +651,162 |
| Patricia, 5/s | 1 | 7 / 7 | 451,028 → 412,937 | 334,762 | 42,343 | +292,419 |

- Quicksort had 176,539 ordinary and 176,954 lease clean BPU misses.
  At 5/s, one seed's two events added little ordinary-arm damage. The
  other seed's single atomic two-bit event at raw logical ages R8/R9
  coincided with 116,481 extra ordinary-arm BPU misses versus clean across
  the run. Its lease arm ended 97 misses below its own clean count. The
  first rebase publication after that event was about 1,323 CPU cycles
  later. The two 20/s pairs saved 126,336 and 248,769 BPU misses,
  comfortably exceeding the measured clean cost in cycle terms.
- Basicmath gained despite three events per arm. Lease removed 13,806
  and 67,568 BPU misses and held the totals within 37 misses of
  its own clean count. A clean-adjusted 154,350–681,132 cycle improvement
  was 4.8–21.3 times its observed clean cost.
- Patricia gained with six or seven events per arm. Lease removed 90,846
  and 38,091 BPU misses and ended within 189 misses of its own
  clean count. A clean-adjusted 334,762–693,505 cycle improvement was
  7.9–16.4 times its observed clean cost.

The discriminating factor in these samples is how much branch disruption
the matched tape produces relative to the workload's cumulative lease
cost. Conditional miss counts fell in every fresh CRC32 pair (10/10),
yet all lost time. They also fell in all fresh Quicksort, Basicmath, and
Patricia pairs (8/8 each). Their runtime wins were 7/8, 8/8, and 8/8,
respectively. Across the low-rate cases with large gains, clean-adjusted
cycle improvement was about 7.6–11.2 cycles per avoided BPU miss.
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
It includes direction counts, accuracy and change from the matching clean
reference in percentage points, direction MPKI, BPU MPKI, O3 commit MPKI,
and both completion cycles and simulated seconds.
Run `python3 analysis/analyze.py --output /tmp/lease4096-pairs.csv`
from the extracted handoff to regenerate it.

## Presentation figures and routed layout images

The presentation handoff includes one plot per workload and a six-page PDF.
Each plot shows TAGE direction accuracy, direction MPKI, and gem5 program
completion cycles at all sampled rates. The dashed references and the
zero-rate markers are the two clean runs. Marker shapes identify paired
seed indices. Within-rate offsets reveal overlap. The solid lines join
per-rate medians. Each new rate has two matched seeds, and the reused
2,000 events/s anchor has eight. The common horizontal axis uses
log10(1 + rate) spacing to retain the zero-rate point.

Cadence Innovus 23.18-s051_1 restored the existing GPDK45 post-route
checkpoints and exported full views, placement-focused views, and the
same 92 × 92 µm routing detail for each design. The matched Lease4096
and SECDED views come from the final route pair documented in
[the routed PPA note](EXPERIMENT_NOTE_2026-11-18_SECDED_PPA.md).
The ordinary recurrent view comes from
`work/history-query-pipeline-route-20261117-r2/attempt2/recurrent/outputs/routed.inn`
and illustrates the baseline from a different routing experiment.
The PNGs represent the staged history subsystem's research layouts.
The checkpoints were opened without changing placement or routing.
