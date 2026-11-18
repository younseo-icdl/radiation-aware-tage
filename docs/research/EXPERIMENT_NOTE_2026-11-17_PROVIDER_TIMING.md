# Native provider selection and table-read timing boundaries

## Question

How much of the remaining query-to-append feedback delay comes from
selecting a prediction after table rows arrive, and how much comes from
reading the rows? The registered history implementation ends at index
and tag outputs. Its measured setup slack is insufficient to establish
arrival of the next speculative direction.

## Provider selection

Implemented `tage_history_provider.sv` for the pinned three-bit
conditional counters, seven tags and fallback. It compares valid
bank tags, selects the two longest matches and applies the native
new-allocation chooser rule. It consumes returned rows and the chooser
and base signals at explicit ports. The RTL result includes direction,
hit bank, alternate bank and provider type.

The C++ vector generator writes selected rows and counter values into
the actual pinned TAGE and calls its production predictor. The
Xcelium gate matched all four outputs over 20,000 vectors and observed
all four provider choices. It used fresh producer
`work/history-provider-gate-20261117-r1/`.

Genus completed at the same nominal slow PVT/500 ps virtual constraints
used for the earlier combinational hash. Area is 600.603 µm² in 343
standard cells. The worst setup slack is -870 ps, on a returned row
tag input to the chosen direction output. The report is a mapped
component observation and leaves the row read, BTB/target selection,
feedback wires and history update outside its scope. Preserve the
answer as a separate path segment and do not add the slack directly
to a CPU clock. Evidence: `work/history-provider-synthesis-20261117-r1/`.

## Tagged row store

Implemented a same-library flop-based 512 × 17 reference row store
for the widest tagged bank. The boundary has two asynchronous row
reads and one synchronous write port. The Xcelium gate checked reset,
read isolation, equal-address reads and visibility on both sides of a
write edge. The model omits multi-update scheduling and the other
table banks, including the T0 base store. This is a reference
implementation for physical characterization of row-read cost.

Gate and Genus producers are `work/history-row-store-gate-20261117-r1/`
and `work/history-row-store-synthesis-20261117-r1/`. The synthesis
requests a dedicated address-to-row timing report. Genus passed on the
reference bank with a 1,210 ps address-to-data path, -835 ps slack
under the 500 ps constraints and 101,733.235 µm² mapped cell area.
The provider-select report gives 1,245 ps data path. These are measured
separate mappings. Combining them requires a concrete circuit and
timing boundary, including the T0 read, data arrival and feedback.
The 65–75% matched history routing remains a separate live batch.

## Matched issue interval mechanism

Added an optional gem5 `--query-ii-cycles`. A conditional query that
actually executes consumes a slot and sets the next permissible issue
tick. Further conditional requests wait until then. This setting can
apply equally to recurrent and lease4096 and measures a throughput
restriction independently of lookup result latency. An issued slot
remains charged if a squash follows. The default preserves existing
callers. Added interval and wait counters appear only when enabled.

The pinned gem5 producer built successfully. The first checksum gate
expected an active stall with a two-cycle interval. Both workloads in
that gate were the same checksum program. Both arms naturally issued
queries at least three cycles apart. The assertion failed while
all four simulations returned the reference stdout. The fresh retry
kept two cycles as a non-binding control and added a four-cycle positive
control. Default-disabled output, native counters, termination record
and activity trace were byte-identical to the prior activity producer
for each corresponding model.

| Mode | Minimum interval, control | Minimum interval, four-cycle test | Wait calls, four-cycle test | Lease publications within capture |
|---|---:|---:|---:|---:|
| Recurrent | 3 cycles | 4 cycles | 8,619 | 0 |
| Lease4096 | 3 cycles | 4 cycles | 8,638 | 5 |

The positive control changed completion by 7,500 ticks (15 cycles) in
each arm of this checksum test. All six runs returned identical expected
stdout. The native regression passed 16 scenarios and five cross-checks.
The finite regression passed all nine clean cases and five injection
cases, including the existing counter, recovery and drain assertions.
The maintained native regression now offers `--query-interval`. It
passed 24 scenarios and seven cross-checks, including both arms with
four-cycle pacing and three deterministic injections. Each injection
applied at its original requested tick and checksum stdout matched.
The maintained gate evidence is
`work/gem5-query-ii-maintained-gate-20261117-r2/audit.json`.
Producers and original failed
assertion evidence are `work/gem5-query-ii-build-20261117-r1/`,
`work/gem5-query-ii-gate-20261117-r1/` and
`work/gem5-query-ii-gate-20261117-r2/`. The checksum controls exercise
the scheduling mechanism at the existing 500 ps simulation setting.
The held-out issue interval still requires a measured implementation
contract.

## Same-tick operand ordering

The activity checker now reports ordered query, append and undo demand
independently of the port-width gate. Reanalysis of the retained clean
qsort prefix found 61,271 of 319,920 queries after an earlier same-tick
append. For 61,249 of those, the tick already contained an earlier query
before an append. The event ordering identifies which ticks need a
timed feedback or scheduling contract. Activity rows lack the producing
query's identity on each append, so the counts are upper bounds on
conditional-to-conditional data dependencies.

The checksum controls contained no query–append–query chains, while
every captured conditional query was followed by an append on the same
tick. A one-query issue restriction removes same-tick chains between
conditional queries by construction. It still requires a closed path
from the issued query to its speculative append. It must also cover
earlier nonconditional appends, table-row arrival, and redirect timing.
The ordering reports from existing captures are in
`work/history-order-audit-20261117-r1/`. This audit launched no workloads.
