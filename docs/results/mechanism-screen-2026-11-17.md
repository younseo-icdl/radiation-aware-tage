# Initial integrated preflight and cheap mechanism screen

No new workload CPU executions were used for this screen. It reuses the three
complete current native U0 committed-query traces; wrong-path lookups and source
operand arrival are not present. Replay/locality outputs do not measure CPU
benefit or actual task energy.

The fixed-environment generator now separately implements SOURCE 2000 events/s,
integer K1:K2=205:9 and contiguous raw130 XOR groups, plus the existing WHOLE
1e15/1e16 per-bit laws and absent-site thinning. Legacy generation is unchanged.
Namespace-v2 descriptors, nominal reference-grid quantization, tape coverage,
equal-timestamp event separation and missing-site counts remain explicit.
Historical tape identity is not asserted without its original generator/tape.

## Content locality and bank profile

Exact per-bank raw-window content is the cache key, not PC. Each bank has an
independent fully associative LRU of 16 or 64 entries; its payload is the three
folds. These are optimistic locality observations before tag/read/compare,
replacement, integrity, port, clock and energy costs.

| Program | H5 hit, 16 | H5 hit, 64 | H130 hit, 16 | H130 hit, 64 | Most selected tagged banks |
|---|---:|---:|---:|---:|---|
| qsort | 93.8054% | 99.9995% | 0.0093% | 15.5061% | 1, 3 |
| dijkstra | 92.1518% | 99.9996% | 42.1749% | 46.7272% | 7, 1 |
| SHA-1 | 99.8723% | 99.9960% | 0% | 0% | 3, 2 |

Key/payload/valid storage across seven per-bank caches is at least 8,176 bits at
16 entries and 32,704 bits at 64, before replacement/integrity/control. H5 has
almost no folding logic to save; high hit rate alone therefore does not justify
a cache. Longer-bank results depend strongly on workload. A generation cache or
rollback cache is a distinct unmeasured mechanism, not an inferred hit rate.

Normalize each workload's provider counts by its committed conditional queries,
then weight the three workloads equally. Tagged banks 1 and 3 have the largest
fractions (20.7687% and 12.4877% of all conditional queries, respectively).
This motivates a **static development** hybrid mask 0x05, with shortest-two 0x03
and longest-two 0x60 controls. It is not an error-criticality measurement, an
oracle, or an independent evaluation; bank selection freezes before fault results.

## Six-family screening disposition

| Family | Current evidence and disposition |
|---|---|
| Lease/rebase | A reusable quiescent protocol waits for actual restore owners, charges service, and publishes Phi of current own raw. Unit/CPU gates cover damaged raw, unchanged learning, age upset and forbidden owner reentry. Measured clean drain cost is below; complete physical cost remains unmeasured. |
| Bank-selective hybrid | Exact mixed hashes pass C++/RTL endpoint checks. Profile mask and simple static controls are shortlisted; no CPU/physical gain is inferred. |
| Maintenance manager | Park until an ordinary lease worker and equal-operation fixed/round-robin comparator exist. It would estimate service utility, not particle arrival. |
| Fold memo/cache | Park the full cache integration pending a cost case stronger than the measured content locality and storage lower bound. No free key comparison or silent-flip detector is assumed. |
| Canonical ahead | Park integration pending wrong-path operand timing, source freshness and rollback protocol. Existing committed traces cannot establish stage fit; incrementing a damaged fold is not canonical precompute. |
| Finite-age segments | Park until simple lease cost motivates extra chunks/selection/undo state. Expiration must not move the error into another persistent accumulator or resurrect it on rollback. |

At most the lease and static hybrid families may proceed to new full CPU/PDK
integration after their gates. These are hypotheses, not winning designs. The
earlier direct candidate and negative eight-owner result remain documented.

## Actual tools and qualification

Local Xcelium 25.09-s010 passed a small original sequential RTL probe. Genus
23.18-s043_1 successfully mapped it into gsclib045 slow cells; Innovus
23.18-s051_1 imported slow/fast views and completed actual placement. This proves
usable tools/licenses for the probe, not TAGE PPA. No administrator package or
sudo change was needed. The initial invalid placement launcher and a missing RTL
timescale attempt are retained; corrected fresh attempts passed.

The new stored/direct/mixed B0 hash RTL passed 20,000 random C++-reference vectors
in Xcelium, including independent inconsistent raw/fold values and mixed-bank
masks. The lease gate is standalone C++; neither establishes O3 or physical
correctness. Matched B0 synthesis is the next physical gate, followed by the
actual source/read/update/undo/control boundary before CPU backannotation.

Private evidence: `work/integrated-preflight-20261117-r1/`,
`work/integrated-placement-20261117-r1/`, `work/integrated-screen-20261117-r1/`,
and `work/rtl-hash-gate-20261117-r1` through `r3`. The package itself is restored
privately under `radiation-aware-tage-private/integrated-handoff-20261117-r1`;
its 60 internal manifest entries passed integrity verification. This package
check does not authenticate historical scientific measurements.

## Matched B0 synthesis, before route

All five variants mapped in Genus with the same slow 0.9 V/125 C library,
medium optimization, 500 ps virtual reference, 50 ps input/output delays,
25 ps uncertainty, 50 ps input transition and 0.01 pF output load.

| Variant | Direct mask | Cells | Library cell area | Reported data path, ps | Worst slack, ps |
|---|---:|---:|---:|---:|---:|
| Recurrent | 0x00 | 621 | 1304.730 | 482 | -106 |
| Full direct | 0x7f | 1448 | 2489.076 | 792 | -417 |
| Profile hybrid | 0x05 | 615 | 1329.354 | 482 | -106 |
| Shortest-two control | 0x03 | 562 | 1254.456 | 476 | -101 |
| Longest-two control | 0x60 | 1524 | 2710.692 | 782 | -407 |

Area is the raw synthesis-library cell-area report, not routed area or complete
history-subsystem area. The input/output/uncertainty budget matters: even the
recurrent block violates this target, so it is invalid to charge an added cycle
only to direct or to declare any of these a qualified full stage. Equal bank
count is not equal circuitry; cross-output optimization/sharing differs.
Retain failures of timing rather than lowering only one design's load or target.

The first elaboration used a named assignment syntax unsupported by this Genus
interface; it failed and was preserved. The positional parameter expression
passed in a fresh producer. Raw artifacts are `work/b0-hash-*-20261117-r*/`, with
the private comparison in `B0_SYNTHESIS_RESULTS.json`. Matched routing and then
the actual B1 storage/read/update/undo/control interface remain separate gates.

## Matched B0 route

All five designs completed the same local place/route flow using slow setup and
fast hold views, fixed floorplan, educational cap-table RC, and virtual clock.
There is no CTS in this combinational boundary. Reports show zero local DRC and
clean signal/special-net connectivity; none meets the 500 ps setup target.

| Variant | Routed cell area | Data path, ns | Setup slack, ns | Fast hold slack, ns |
|---|---:|---:|---:|---:|
| Recurrent | 2250.360 | 0.551 | -0.176 | +0.137 |
| Full direct | 4452.840 | 0.991 | -0.616 | +0.075 |
| Profile hybrid | 2146.734 | 0.585 | -0.210 | +0.079 |
| Shortest-two control | 2061.234 | 0.585 | -0.210 | +0.079 |
| Longest-two control | 4480.884 | 0.974 | -0.599 | +0.139 |

Cell areas include mapped buffering/inversion, not raw storage, undo, controller
or a full predictor. Different post-route optimization means the hybrid's lower
cell area is not a full-subsystem saving. No activity-based energy is available.
The route evidence is `work/b0-route-{recurrent,direct,profile,short,long}-20261117-r1/`.
Do not backannotate a zero-latency recurrent block or charge only direct for a
failed physical target. Source/read/port/restore delay is still absent from B0.

## Clean CPU controls and actual interface demand

Nine new runs completed, with exact expected stdout, architectural retirement
identity and complete BPU joins. Native and hybrid use the same 500 ps CPU grid
with no physically qualified hash delay (C0). Lease additionally pays actual
admission stop/owner drain and an assumed two-cycle publication service.

| Program | Native cycles | Lease64 cycles | Lease64 vs native | Hybrid05 cycles |
|---|---:|---:|---:|---:|
| qsort | 34,485,063 | 37,878,057 | +9.8390% | 34,485,063 |
| dijkstra | 40,991,213 | 43,067,795 | +5.0659% | 40,991,213 |
| SHA-1 | 5,905,076 | 6,093,489 | +3.1907% | 5,905,076 |

Hybrid05 has exactly the native clean stream and cycles under this C0 model;
this is not a physical M0 cost result. Lease timing can change predictor training
visibility and accuracy, so its measured total cost is not a pure stall penalty.
Raw logs, stats, native summaries and full native traces are retained under
`work/integrated-clean-20261117-r1/`.

Native qsort/dijkstra/SHA-1 respectively observed peak live restore-owner counts
46/46/42, conditional queries per tick 2/2/2, raw appends per tick 3/2/3, and raw
undos per tick 45/45/29. The declared CPU owner capacity remains 512; observed
46 is not a universal bound. A one-query/one-undo physical design would not
implement this CPU contract. Unused software fold snapshots must not be charged
as consumed checkpoint state: the pinned restore uses an algebraic inverse.

`tage/history/bulk_restore.hpp` establishes the identity
`F_after = Phi(H_after) XOR ROTR(F_before XOR Phi(H_before), n mod width)`
for up to 512 undos. Both windows must come from the current live raw ring.
63,000 comparisons against the pinned sequential restore cover all counts
0..512, circular wrap and arbitrarily inconsistent raw/fold state. This retains
fold residuals and raw-upset effects; replacing restore with canonical rebuilding
would silently repair the recurrent baseline. The kernel is not integrated into
CPU timing and gives no free read alignment, restoration port or latency.

Before observing SOURCE fault outcomes, a lower-frequency lease4096 control was
declared because lease64's clean cost is substantial. The development batch has
three new lease4096 clean runs and 24 SOURCE fault runs: three programs, two
frozen development owners, and native/lease4096/hybrid05, plus qsort controls
lease64/hybrid03/hybrid60. Three bounded atomic-K2 gates passed first. Fixed
2000/s exposure is unchanged; this is development, not independent evaluation.
See the private `work/integrated-source-dev-20261117-r1/SOURCE_DEV_PLAN.json`.
