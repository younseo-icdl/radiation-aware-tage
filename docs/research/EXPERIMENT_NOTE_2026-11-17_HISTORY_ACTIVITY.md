# Ordered history activity for physical measurement

## Question

Can an operation trace reproduce the actual history inputs a routed RTL
block would consume? The committed CPU trace misses wrong-path activity
and cannot reconstruct owner checkpoints or exact undo ordering.

## First implementation

The optional `--activity-end-tick` captures a clean run's prefix from
reset. The end tick is exclusive. CSV order records actual conditional
query addresses, raw and path appends, each restore, owner release, and
lease service start and publication. Owner identifiers are local stable
observer IDs for appended histories. Redirect correction can restore and
append again using the same owner. Owner IDs are not physical slots.
Unknown restore ownership and append widths outside the single-bit
contract fail the capture. The commit trace and RNG sequence are
independent of this observer. The existing CLI remains usable on older
gem5 builds when the capture option is absent.

Use a fresh gem5 producer based on the pinned existing integrated tree
and compare observation-off and observation-on bounded checksum runs for
both methods. Compare exit tick, stdout, retirement/lookup fingerprints,
append counts and publication edges. Check owner and operation ordering.
Run the native and finite checksum gates on the new producer before
admitting workload activity. These gates are pending while it builds.

`simulation.analysis.history_activity` now checks the ordered capture.
It tracks append owners, stack-ordered undo and correction, release,
service start and exact publication. It counts port demand and reports
operations that cannot be grouped into the current undo-first RTL edge.
A same-tick publication plus normal work is a scheduling question in
this grouping. It does not by itself show an incorrect CPU trace.
Three focused Python tests passed for correction, interleaving and
service-boundary rejection. The real capture gate uses a 40,000,000 tick
exclusive window on the checksum with and without full-bank lease4096.
Private build and gate producers are `work/gem5-activity-build-20261117-r1/`
and `work/gem5-activity-gate-20261117-r1/`. Workload tracing remains gated
on the bounded checks. The observer functions are inactive by default.

## Use in power comparison

A later replay step must allocate bounded physical owner slots and check
same-edge resource limits and event ordering before conversion to RTL
stimulus. In particular, an undo interleaved with queries or appends may
need a different delivery contract than the current RTL's undo-first
interface. Preserve and report such a mismatch. Driving precomputed
operands measures the history block and its own switching. Runtime and
feedback scheduling still require the held-out physical timing gate.

## Bounded capture result

The independent eight-job build from source 17bd5bc completed. The
four checksum executions agreed within each capture-off/on pair in
stdout and complete `native.json` bytes. Exit was at 43,216,000 ticks
for native and 43,280,500 for lease4096. The new producer passed all
16 native cases, all five native cross-checks and all 14 finite
checksum cases.

| Capture, ticks [0, 40,000,000) | Queries | Appends | Undos | Publications | Peak append owners |
|---|---:|---:|---:|---:|---:|
| Native | 18,618 | 23,950 | 78 | 0 | 14 |
| Lease4096 | 18,592 | 23,916 | 78 | 5 | 14 |

The native prefix had no conflict under the conservative grouping
checker. Lease4096 had two publication ticks followed by an append
at the same tick, 13,767,000 and 34,283,500. The simulator callback
order was publication then append. RTL's publication branch excludes
append at the same active edge. A plausible replay maps publication to
the opening edge and the later CPU operation to the following edge.
This needs an explicit RTL phase check before using the capture as
power stimulus or crediting the gem5 timing. The checksum has only
one query and one append per observed tick. Wider workload feeds
still need their own audit.

Commands, fingerprints, trace counts and reports are saved under the
private `work/gem5-activity-gate-20261117-r1/`. The old producers are
retained. No held-out workload ran.

The Xcelium lease test now also drives an append after the publication
edge and checks that the following edge advances the head and updates
the newly canonical fold. This directed sequence passed in
`work/b1-lease-phase-gate-20261117-r1/`. It establishes the RTL phase
ordering for this case. A complete trace replay must still reconcile
all service start, publication and operation edges independently.

## Full bounded RTL trace replay

The replay now uses the complete checksum capture for each method.
`simulation.analysis.history_replay` allocates up to 512 physical
checkpoint slots. It defers reuse of slots released within the current
edge and rejects unsupported undo ordering, port demand and off-grid
operations. CPU operations at tick T drive the interval ending at
T + period. An autonomous publication is checked at the opening edge T.
This preserves the two observed publication-followed-by-append cases.
The service input is driven from the recorded quiescent service window.
It does not impose unrecorded work on the RTL.

Xcelium passed 80,001 edges for each method with the 500 ps capture
grid. The test checks the raw window, path value and ring head at
every edge against the independent replay state. It checks the
publication pulse against the trace before each edge. Native recorded
zero publications and lease4096 recorded five, all at the expected
edges. Hash values during the functional trace use the RTL logic
already covered by the separate production-reference vectors.

The first replay passed in `work/history-replay-20261117-r1/`. The
independent rerun with releases deferred within an edge passed in
`work/history-replay-20261117-r2/`. Retain both vector sets, console
logs and VCDs. The VCD scope is `history_activity_tb`. Each simulation
also accepts `+period_ps` to drive the same edge sequence at the
reported common physical period once timing allows.

Use the 500 ps VCDs for functional evidence. A fresh matched-period
pair is required for the registered power estimate. The two methods
have their own actual checksum activity, including idle intervals
and undo. An estimate over this prefix uses port annotation and
tool propagation of internal activity. It will report coverage and
bounded history-block power. Full task energy needs qualified clock,
complete activity and measured run duration. Provider feedback still
needs a timing contract before held-out CPU performance.

## Development qsort burst check

One clean development qsort execution captured the first 500,000,000
ticks. It exited successfully at 17,242,531,000 ticks and matched
the retained output. Comparing native summaries isolated one expected
difference: the earlier diagnostics run retained ten branch observation
frames at exit, while this activity-only capture retained zero.
The first replay stopped at an overly strict whole-file equality
assertion. The second explicitly checked the single expected metadata
difference before proceeding. All performance and state fingerprint
fields agreed.

The capture contained 319,920 conditional queries, 407,487 appends
and 30,299 single-bit undos. Peaks were two queries, three appends,
30 undos per tick and 45 allocated append owners. The ordered validator
found no edge-grouping conflict in this prefix. The Xcelium replay
then passed 1,000,001 registered history edges against the independent
raw, path and head model. This exercises the wider input shape beyond
checksum. It does not time the external prediction result or owner
allocator. No held-out workload was opened.

Private sources: `work/qsort-edge-demand-20261117-r1/` and
`work/qsort-history-replay-20261117-r2/`.
