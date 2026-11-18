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

This is a scheduling mechanism for a potential measured common
contract. The test below uses a two-cycle interval to exercise the
gate, rather than selecting the held-out policy or asserting a
two-cycle measured path. The test will verify adjacent conditional
query gaps, observability of stalls, exact checksum stdout, lease
publication and original disabled behavior. New producer and gate
outputs are `work/gem5-query-ii-build-20261117-r1/` and
`work/gem5-query-ii-gate-20261117-r1/`.
