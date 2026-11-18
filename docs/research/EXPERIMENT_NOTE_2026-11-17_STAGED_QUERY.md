# Registered query and speculative append

The routed history layouts at 8.100 ns closed history-only STA. The
latest no-undo query outputs and the append input deadlines left the
table-row and direction return path unqualified. This experiment uses
the same staging in both arms. The full-bank lease period stays 4096,
and the existing paired SOURCE coordinates, seed set and evaluation
workloads remain frozen.

## Interface

A conditional query retains one packet containing the PC, tagged row
indices and tags, request token, checkpoint owner and path bit. The
returned rows feed the ordinary longest/alternate/bimodal selection.
The speculative append uses the taken direction only when target
handling supplies a valid target. An older undo or external history
append, redirect, or maintenance invalidates a pending packet before
it can update history. A stale token cannot append. The consumer can
hold an outstanding packet under backpressure. Request and response
occupy distinct edges, and the issue edge contains no external
history write. The packet and the active restore owners clear before
lease publication.

The opt-in gem5 mode uses the existing O3 fetch ownership hook.
It captures recurrent indices and tags into the request at issue, then
uses them for upstream row selection on response. An architectural
history mutation invalidates the packet. A stored-bit event does not
invalidate a hash already captured. Normal table training continues
in gem5's existing order. The optional clean history activity trace
records the query at hash capture. Committed branch diagnostics with
both hash and row times will need a stage-aware record.
The default and existing explicit issue interval retain their old
configuration and behavior.

## First validation

The Xcelium tests passed ordinary mode and an intentionally shortened
period-2 lease. The bench verified a stable captured packet, stale
response rejection, target-miss fallthrough, cancellation before a
ready response, priority of older rollback, single append and
quiescent two-cycle publication. The production period remains 4096.
Private logs are in `work/history-query-pipeline-rtl-20261117-r1/`.

The fresh pinned gem5 producer and the two matched Genus producers
are running under `work/gem5-query-pipeline-build-20261117-r1/` and
`work/history-query-pipeline-synth-20261117-r1/`. The bounded CPU
gate checks output and retirement identity, cancellation, ownership,
the original absolute injection tick and consumption of registered
operands when an inter-stage fold upset changes a fresh hash. The
fault in that check is a directed logic test. It does not alter the
held-out raw-only event law. Actual tagged/base row availability,
training order at the physical memory boundary and target timing
remain separate from registered state closure.

## First build and synthesis results

The first pinned build compiled and both clean staged checksum runs
passed. Each accounted for 20,054 responses and 11 canceled requests,
with no outstanding request at exit. The first hash capture was
122,000 ps and its response was 122,500 ps in the functional test.
Lease4096 published six times. Both first inter-stage fault checks
reached architectural exit with correct stdout and applied the flip
at 122,001 ps. Their diagnostic assertion failed because it monitored
the history callback epoch, which does not advance on injection.
A fresh build tests against the explicit applied-event count and
checks that exactly one pending response faced a changed recomputed
hash. Failed and retry results remain in
`work/gem5-query-pipeline-gate-20261117-r1/` and
`work/gem5-query-pipeline-gate-20261117-r2/`.

The matched 8.100 ns Genus runs completed. Returned table rows entered
at the same 50 ps reference delay used by the first layout. The
feedback measurement includes provider selection, target-valid
gating and the actual speculative append to a state register.

| Mode | Mapped area (µm²) | Worst setup slack | Returned-row to state setup slack |
|---|---:|---:|---:|
| Recurrent | 158,798.124 | +596 ps | +3,823 ps |
| Lease4096 | 158,397.710 | +426 ps | +3,986 ps |

The mapped area difference is small in the staged design. The
previous layout's area and energy deltas belong to the earlier
history interface. The fresh common routing trial uses a planned
523.512 µm die side, with an automatic check of actual area and
utilization. Routes and matched CPPR STA are in
`work/history-query-pipeline-route-20261117-r1/` and
`work/history-query-pipeline-sta-20261117-r1/`.

T0's prediction bit is read independently from its hysteresis state.
The reference has 8,192 prediction bits and leaves hysteresis
training outside the read path. The first Genus attempt stopped at
the default 4,096 HDL loop limit. The second raises that tool limit
while preserving the native table depth. The reference placement
queue will characterize the T0 address-to-bit path and the widest
tagged row address-to-data path on separate extracted layouts.
Its output is `work/history-row-reference-route-20261117-r1/`.
The new STA option can apply a measured late row arrival without
changing hold constraints. It does not substitute for the remaining
row ordering, target arrival and memory-write capacity checks.

## Retry of the staged checker and burst observations

The second build and gate passed 28 native cases and 11 cross-checks,
plus the finite 14-case checksum gate. The disabled mode reproduced the
prior producer's native summary, termination and stdout byte for byte.
Each deliberate fault survived after the captured hash and changed a
freshly recomputed hash for exactly one pending response. Both arms
retired 233,030 instructions in the reference program order. The
lease arm published six times. This was a functional 500 ps test,
before physical backannotation.

Within the 40 million-tick capture, each arm reached one hash issue
and one append per tick, up to six undos and eight live replay owners.
No issue followed an append or undo on the same tick, and no append
followed an issue on that tick. Lease publication shared a tick with
an append once and with a hash issue once, with publication recorded
first. The corresponding RTL control phase still needs an explicit
edge-level replay. Reports are in `work/history-staged-order-audit-20261117-r1/`.

Analysis of the older unpipelined native traces found maximum
conditional training demand of three calls per tick for qsort and
two for dijkstra and SHA-1. Qsort had 857,104 ticks with two calls
and 65 with three. These count training calls, not separate writes
to any particular bank. A single-write reference memory gives a
read-path estimate. It does not establish the physical throughput
of gem5's training path. The archived counts are under
`work/history-training-order-audit-20261117-r1/`.

The T0 mapping retry passed. Its address-to-prediction data path is
2,360 ps at the synthesis stage and +5,615 ps slack with the 8.100 ns
reference constraints. This includes neither routed interconnect nor
the registered history block's downstream path. Separate tagged and
T0 route jobs started for those read boundary measurements.

## Cycle edges and scan-cell placement retry

The first staged gem5 test captured the hash at request admission
and charged a cycle before reading rows. The physical circuit has a
distinct request interval before the hash register edge. The next
producer schedules that latch one cycle after admission. Row
consumption follows no sooner than the next cycle. An upset between
admission and the latch is visible when hashing. An upset after the
latch leaves the captured hash unchanged. The gem5 fault event runs
before the latch at the shared tick, and redirects invalidate the
outstanding packet before an append. The directed gate places one
event in each interval and compares the first consumed hash identity.
New results are under `work/gem5-query-pipeline-gate-20261117-r3/`.

The initial staged recurrent placement stopped on Innovus
`IMPSP-9099`. Genus had chosen scan-capable flops as a functional
enable mux. For example, a checkpoint bit fed its own Q back to SI,
with the write-enable signal on SE. The design has no DFT chain.
Innovus also reported the issue in the lease arm, where placement
continued below the tool's fatal threshold. Its partial evidence is
retained separately. The paired remap excludes the scan-flop families
in both variants and checks that the mapped files contain none. It
keeps the same RTL, Liberty and timing constraints. The remap and
replacement layout use `work/history-query-pipeline-synth-20261117-r2/`
and `work/history-query-pipeline-route-20261117-r2/`.

The two-edge CPU producer passed 30 native scenarios and 13
cross-checks, the 14-case finite checksum gate, and `make test`.
Both arms issued at 122,000 ps, captured at 122,500 ps, and first
consumed rows at 123,000 ps in the 500 ps functional test. The
122,001 ps flip changed the first latched hash. The 122,501 ps
flip left that hash equal to clean while a new computation differed.
Each applied at its requested tick. Both arms preserved the clean
retirement identity and the lease arm still published six times.

The staged qsort prefix retained conditional training bursts at
two calls in the same tick. It had 635 such ticks in recurrent and
633 in lease at the same 100 million-tick exposure. This is new
evidence from the staged configuration, separate from the archived
unpipelined counts. It motivated a matched optional single conditional
training port. That mode reserves credit through O3's existing
retirement hook, stalls only a conditional retirement with no
available credit, and checks the actual upstream training callback
width. The reservation does not reorder or replace the upstream
training algorithm. Both modes use the same setting.

The new producer passed 32 native scenarios and 15 cross-checks,
and the finite 14-case checksum gate. The port-limited clean
checksum had 20,016 completed conditional training calls per arm
and zero waits. A distinct qsort prefix exercised the limit.

| Mode | Conditional training calls | Maximum calls per tick | Port waits |
|---|---:|---:|---:|
| Recurrent | 42,348 | 1 | 639 |
| Lease4096 | 42,215 | 1 | 641 |

The qsort test stopped at its predefined tick, before architectural
exit. It validates the scheduling cap and supplies no task runtime
comparison. Logs are in `work/gem5-query-pipeline-gate-20261117-r4/`,
`work/history-staged-training-audit-20261117-r1/` and
`work/history-training-port-qsort-20261117-r1/`. A single conditional
update call can update several arrays. The throughput check does not
measure the table-training logic or the parallel usefulness aging
operation.

The first extracted array references missed the 75% die-utilization
limit. Their address-to-data delays were 4.817 ns for the tagged
reference and 5.490 ns for T0. These are useful diagnostics for why
the mapped row-to-history slack cannot by itself establish an 8.100 ns
pipeline clock. Both fresh reference routes reached the density range
at 73.631% and 74.617%, respectively. A new audit checks CPPR hold
and extracted path delays on the accepted layouts.

The composed timing check uses extracted register-to-address and
separately extracted address-to-row delays. It includes a declared
100 ps unplaced boundary-link allowance and tests the same late
deadline on the external target-valid input. The deadline is an
interface bound, with no measurement of target lookup or cross-block
routing at that boundary. It reruns STA with the late data constraints
and then triggers a bounded checksum gate at the resulting candidate
period if timing passes. Results are isolated from the held-out
workloads in `work/history-composed-timing-20261117-r1/` and
`work/history-composed-checksum-20261117-r1/`.

The two-edge, port-limited checksum trace reported three ticks per
arm with a hash capture preceding an older undo. The per-tick width
was still one hash, one append, and at most six undos. The existing
unstaged replay cannot tell whether the captured hash was subsequently
discarded. Its conflict check is left intact. A staged trace must
carry the request identity through capture and cancellation to verify
this ordering against the RTL.
