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
requests a dedicated address-to-row timing report. Result pending.
The tool's initial -870 ps on selection and the row-store result can
inform a complete staged or dependent path, but neither certifies a
second query using a first query's direction in the same cycle.
The 65–75% matched history routing remains a separate live batch.
