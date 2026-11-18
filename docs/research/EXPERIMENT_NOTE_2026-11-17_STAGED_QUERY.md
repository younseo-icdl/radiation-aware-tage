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

The two-edge, port-limited checksum trace reported three undo
operations per arm after a same-tick hash capture. The per-tick width
was still one hash, one append, and at most six undos. The existing
unstaged replay cannot tell whether the captured hash was subsequently
discarded. Its conflict check is left intact. A staged trace must
carry the request identity through capture and cancellation to verify
this ordering against the RTL.

The new clean trace records query request, hash capture, row response
and cancellation under one token. The validator requires a live
matching token, distinct ordered edges, and a same-tick append after
response. It rejects a response if an intervening undo or append
invalidated the captured history. The ordinary trace and replay
format remain available. The old replay explicitly rejects the new
staged trace so it cannot silently interpret a hash capture as a
completed query. The fresh producer checks trace transparency
against the verified port-limited checksum, under
`work/gem5-query-pipeline-gate-20261117-r5/`.

The density-qualified extracted references report 5.074 ns for the
tagged read at 73.631% and 5.637 ns for the T0 read at 74.617%. The
tagged checkpoint passed its matched CPPR timing audit, including
+31 ps hold slack. T0 passed read/setup checks but had -10 ps hold
slack on the external write-address-to-cell path. The composed
timing gate stopped there. An isolated ECO removes fillers before
hold optimization, then repeats detailed routing, RC extraction and
physical checks without replacing the original checkpoint. It is
under `work/history-t0-hold-eco-20261117-r1/`.

The structured trace producer passed 32 native scenarios, 15
cross-checks, the finite 14-case checksum gate and 68 Python tests
with the C++ suite. With tracing enabled, staged native summaries,
termination and stdout are byte-identical to the prior producer.
In each arm token 23 captured at 188,000 ps, then all three undo
operations occurred on that tick and canceled that token. No row
response or speculative append used the canceled hash. The
lease trace also retains an unfinished request at its exclusive
capture bound. The observation resolves the old trace ambiguity
without treating an older undo as an executed prediction.
The strict clock-grid audit checked every latch one cycle after its
request. The 14,495 recurrent and 14,482 lease responses in the
captured windows all occurred one cycle after their latch. This
reused the existing capture and is retained in
`work/history-stage-clock-audit-20261117-r1/`.

Both scan-free staged remaps completed. Mapped area is 164,120.054
µm² for recurrent and 159,185.952 µm² for lease. At 8.100 ns,
overall setup slack is +266 ps and +298 ps, and returned-row to
state slack is +3,795 ps and +3,555 ps, respectively, with the
50 ps reference input arrival. The first fresh common die is
528.389 µm per side. Actual utilization and paired CPPR STA are
still in progress.

The first T0 ECO stopped on an unsupported plural filler command.
The installed tool supports `delete_filler`. The fresh retry
completed placement and routing, but its external write hold
remained at -11 ps. The original restored checkpoint had two
violating sinks on the same input bit, `write_addr_i[2]`. A
separate ECO inserts one data-pin repeater at each sink, then
rechecks extraction, setup, hold, connectivity, DRC and the
die-utilization rule. Both failed attempts remain available.
The first targeted command treated escaped bus-pin names as braced
list elements and did not insert repeaters. A fresh invocation
passes each pin as a single Tcl string. The original two violations
and all retry artifacts are preserved.

The prospective benchmark manifest was rechecked without running
the held-out programs. All 16 locked files matched their recorded
SHA-256 digests.

## November 18 physical and trace replay checks

The scan-free attempt completed both routes at the first common
die size. Recurrent and lease utilization were 80.418% and
78.660%, above the required range. A fresh common 563.349 µm
die is running, using the placed cell areas from the first attempt.
The attempt-1 reports remain under
`work/history-query-pipeline-route-20261117-r2/attempt1/`.

The exact-pin T0 ECO inserted two BUFX2 repeaters at the diagnosed
data sinks. The restored layout passed DRC, signal and supply
connectivity, +3 ps fast hold, and +2,338 ps slow setup. Its die
utilization is 74.6194%. The extracted address-to-data delay stays
5,637 ps. The approved reference pair and its timing are in
`work/history-composed-timing-20261117-r3/REFERENCES.json`.
The staged matched STA and late-arrival checks still precede the
timed checksum and held-out gates.

A fresh Xcelium replay used the structured port-limited CPU
traces on the staged history wrapper. It applies the row response
on its recorded edge and moves ordinary append/undo operations to
their closing edge. For the captured redirect at 188,000 ps, the
cancel suppresses the packet while the older undo takes its
normal state edge. The replay compares live token, raw ring
window, head and path at every edge, and checks response and
publication admission. Both modes passed 80,001 edges.

| Mode | Accepted row responses | Canceled captured queries | Lease publications |
|---|---:|---:|---:|
| Recurrent | 14,495 | 1 | 0 |
| Lease4096 | 14,482 | 1 | 4 |

The bench uses the observed speculative direction as a synthetic
bimodal row response. The results qualify the interface event
sequence and history state during this trace. They do not measure
row-selection activity, table training, routed switching energy,
or full CPU performance. The private inputs and replay logs are
under `work/history-pipeline-activity-replay-20261118-r1/`.

## Actual returned-row activity

Added an optional clean capture of all seven returned tags and
signed counters, the bimodal bit, bank enable and alternate chooser
state, and the BPU's actual target-valid decision. Each record
carries the same token as its history response, the PC, the saved
query indices/tags, and the selected conditional direction. The
observation takes row values at upstream selection and joins the
target after BPU handling before discarding its temporary record.
Legacy traces and timing modes keep their existing outputs.

The expanded replay verifies the stored indices/tags and provider
direction on each actual response alongside the speculative append
and history state. Invalid row intervals retain the previous
captured bus values for the activity estimate. With a routed
netlist present, Xcelium checks its controls, operand outputs and
feedback against RTL and can emit a gate-level waveform. This is
an observation of timing inputs and switching under the captured
sequence, not a separate implementation of TAGE table training.

The new pinned producer and bounded gate are under
`work/gem5-staged-rows-build-20261118-r1/` and
`work/gem5-staged-rows-gate-20261118-r1/`. After the measured
composed timing and timed checksum gates, the power coordinator
captures both arms at the common period, trims them to a common
pre-exit window, and imports the checked waveform into Innovus.
Its outputs are under `work/history-staged-power-20261118-r1/`.

The first returned-row run passed the normal gem5 regression and
reproduced the prior native state, program output, termination and
history trace. Its new CSV still had a truncated buffered tail at
exit. The complete 14,483 responses before tick 39,968,000 passed
the exact-index, exact-tag and direction checks across 79,937 RTL
edges in a separately derived prefix. The original capture was
preserved. The fix flushes the companion row stream at the same
architectural-exit hook as the other observers and rejects a
partially written record. The full paired retry is under
`work/gem5-staged-rows-gate-20261118-r2/`. Its corresponding power
consumer is `work/history-staged-power-20261118-r2/`.

The private held-out runner passed a read-only prospective check
of the exact three manifests, 24 locked event seeds, eight
parallel workers, and the 54-case plan. It uses the fixed SOURCE
generator and the existing owner-bootstrap analysis. No held-out
workload was launched. The artifact and seed inventory is under
`work/heldout-planning-20261118-r1/preflight/`.

The flushed paired retry passed 32 native cases, 15 cross-checks,
the 14-case finite checksum gate, and all C++/Python tests. The
full trace replay passed 80,001 edges in each arm. Every live
returned-row packet matched the CPU hash and target-gated direction.
That covered 14,495 responses for recurrent and 14,482 for
lease4096, including one cancellation in each arm and four lease
publications inside the capture. The four original CPU artifacts
remained byte-identical with the extra row observer enabled.

Both scan-free staged layouts completed at the second common die
size of 317,498.436 µm². Utilization is 72.979% and 72.630%.
Placed cell area is 231,706.026 and 230,599.998 µm². These layouts
passed DRC and the signal and supply connectivity checks.
At the preliminary 8.150 ns recheck with CPPR, recurrent passed
+78 ps setup and +22 ps hold. Lease passed hold at +3 ps and
failed setup by 173 ps on restore owner to checkpoint. This
stopped the preliminary gate. The two measured returned-row
feedback slacks were +2,177 ps and +969 ps under the original
50 ps input constraint.

The next paired STA directly uses the measured restore deficit
and the row timing composition. No beneficial negative launch
skew is credited across separately placed blocks. The latest
registered address path is budgeted at 904 ps, the slower
extracted reference read is 5,637 ps, and the explicitly unplaced
link allowance is 100 ps. The returned-row input and the
externally asserted target-valid deadline are constrained to
6,641 ps. The larger feedback deficit is 5,622 ps from the
8,150 ps recheck. The candidate common period is 13,850 ps,
using the 50 ps upward rounding and additional 50 ps margin.
The fresh STA, then conditional timed checksum and matched
activity-power outputs, are under
`work/history-composed-timing-20261118-r4/`,
`work/history-composed-checksum-20261118-r3/`, and
`work/history-staged-power-20261118-r3/`. The target deadline
and cross-block allowance are explicit interface assumptions.
The physical scope does not include the external target lookup.

The paired late-arrival STA passed at 13.850 ns with +1,286 ps
setup and +22 ps hold for recurrent, and +189 ps setup and +3 ps
hold for lease. Both checks used the same 6,641 ps late data and
target-valid constraints and CPPR. The bounded gem5 suite at
13,850 ticks per cycle also passed, including inter-stage fault
ordering, exact checksum and retired identity, single-port
retirement, and fixed two-cycle lease service.

The first routed power replay stopped at elaboration because the
routed provider submodule and the RTL reference used the same
module name. Its modified physical ports were bound to the
unmodified RTL module. The retry renames only the simulation
copies of the reference RTL modules and reuses the same frozen
layout, row data and edge vectors. That preserves the physical
net and scope names for power annotation. It is under
`work/history-staged-power-20261118-r4/`.

The target-valid signal is independently characterized at the
external boundary. The reference uses the frozen single-thread
SimpleBTB geometry of 4,096 direct-mapped entries, a 12-bit
index, and a 16-bit tag plus valid bit. The directed RTL gate
passed insert, tag collision, hits at both ends of the index
range, replacement and invalidation. Target payload, return
stack and indirect prediction are outside this reference. Genus
and route producers are under `work/history-btb-reference-20261118-r1/`
and `work/history-btb-reference-route-20261118-r1/`. A separate
STA diagnostic isolates the target input to the staged state
registers at the current shared clock, in
`work/history-target-arrival-audit-20261118-r1/`. The timing
deadline must be compared to measured generation before using the
candidate period for held-out conclusions.

The target-only STA reports +4,554 ps and +3,271 ps of slack at
the same 6,641 ps input constraint in recurrent and lease.
The limiting latest target arrival across the matched pair is
therefore 9,912 ps at 13.850 ns. The measured reference route is
queued after the live Genus job. Its follow-up will combine the
registered PC path with the extracted hit path without taking
credit for negative launch skew, then recheck the actual target
budget on both layouts. Results will be under
`work/history-target-budget-20261118-r1/`.

## Staged activity-based power at 13.850 ns

The namespace-isolated routed replay passed 80,001 edges per
arm with the actual rows, chooser state and target validity from
the timed checksum runs. It compared 14,532 ordinary and 14,519
lease responses, one cancellation per arm and four lease
publications. Both designs directly annotated every net, every
flop output and all 237 primary input bits. They used the slow
0.9 V view for the common 1.10801385 ms window.

| Mode | Internal (mW) | Switching (mW) | Leakage (mW) | Total (mW) | Window energy (µJ) |
|---|---:|---:|---:|---:|---:|
| Recurrent | 1.49128 | 0.65926 | 0.005431 | 2.15597 | 2.38884 |
| Lease4096 | 1.53668 | 0.72973 | 0.005481 | 2.27189 | 2.51729 |

Lease used 0.48% less placed cell area and 5.38% more
history-window energy in this staged layout pair. Its estimated
switching power was 10.69% higher. The previous interface's
11.68% reduction was measured on different layouts and a
different clock and activity window. The two comparisons cannot
isolate which RTL or placement change caused the reversal.
The current gate-level activity has zero cell delay. The
estimates cover the history datapath and returned-row selection,
with no power from separate lookup arrays, the external frontend
or the full program. Routed reports are under
`work/history-staged-power-20261118-r4/`.

At the same candidate period the checksum clean runs completed
at 1,529,538,600 and 1,530,965,150 ticks, a 103-cycle
lease overhead. This is bounded checksum evidence. The held-out
programs remain unopened.

Both timed checksum arms recorded 20,052 direct conditional
lookups and zero indirect conditional lookups. The held-out
runner records the same counters and treats any nonzero or
missing indirect count as outside the measured target-path scope.
It retains such runs and excludes them from comparative timing.

### Held-out admission and SOURCE delivery audit

The native checksum audit now records SHA-256 digests of gem5,
the simulation configuration, its common CPU configuration, and
the checksum binary. The private held-out runner binds the two
timed checksum arms to the execution period and exact simulator
and configuration hashes. Admission requires the measured direct
BTB reference and passing paired late-arrival STA. If the final
clock changes, the activity-power replay must match it before
launch. The admission coordinator is waiting on the live reference
producer. No held-out workload was opened.

The SOURCE checker regenerates the declared tape, compares each
applied record against the absolute-tick prefix at architectural
exit, and verifies raw sites, contiguous multiplicity, XOR, and
censoring against the native log. Equal-tick records stay distinct.
It passed on the twelve retained development recurrent/lease runs
and a fresh paired checksum at 13,850 ps with a shared diagnostic
SOURCE tape. Each checksum arm applied one event and retained
twenty future records. The checksum control and its frozen-config
regression are under `work/heldout-planning-20261118-r1/`.

### Banked physical layout of the direct-target reference

The flat 4,096-row reference was still using CPU time after
58 minutes, while the mapping workers remained idle. An
independent producer organizes the same 4,096 entries as
eight 512-row banks and preserves their hierarchy during
mapping. The low nine index bits address a row, and the
high three select its bank. The selected valid bit and
16-bit tag use the original comparison.

The paired RTL gate filled all 4,096 indices and checked
a hit and a conflicting tag at each index for both layouts.
It also checked replacement and reset. Both synthesis
producers retain separate logs and route directories. The
single admission process accepts the first physically
qualified target budget, then reruns the timed checksum
with the exact frozen configuration and checks the matching
power period. Neither the fault law nor the two predictor
policies depends on the reference layout. The banked
producer and admission controller are under
`work/history-btb-reference-20261118-r2/` and
`work/heldout-admission-20261118-r2/`.

The banked map reached a synthesis partition and dispatched
work to a mapping worker. The flat producer was still active.
The latest private coordinator under
`work/heldout-admission-20261118-r3/` also handles a clock
change by rerunning the paired activity replay and checking
full annotation before admission. It reuses the recorded
13,850 ps replay if the clock remains unchanged. No
held-out run was started by this change.

The banked reference synthesis completed successfully. The area
report retains all eight 512-entry banks and gives 684,885.780 µm²
before placement. At the slow 0.9 V synthesis corner Genus
reports 3,359 ps for the read-PC to hit path and +10,366 ps
setup slack at 13,850 ps. These are wireload results. The
fresh physical producer is in CTS under
`work/history-btb-reference-route-20261118-r2/attempt1/`.
Extracted read, write hold, DRC, connectivity and die utilization
are pending. The flat synthesis was still using CPU time and is
retained as an independent producer.

The banked placement completed CTS and reached post-route hold
optimization. Its initial optimization snapshot reported 69,632
violating paths and -290 ps WNS. These are intermediate tool
figures, before final extracted CPPR recheck. Both the final
hold constraints and final die utilization remain required.
The flat synthesis has since entered four-way partitioning.
The admission controller has not opened the workload inputs.

The first banked layout completed at 83.503% die utilization
and is outside the range. Its extracted CPPR audit measured an
8,710 ps read-to-hit path and -185 ps write hold slack. The
limiting path starts at `write_pc_i[0]`. At that endpoint the
capture clock insertion is 362 ps and the input delay plus data
path is 204 ps. The new larger-die run is in placement. The flat
reference also completed synthesis and is routing separately.
The first banked checkpoint remains available for diagnosis.

An isolated physical pilot inventories early paths from the
write, enable and reset inputs, then inserts a non-inverting
repeater chain on the worst write input. It reroutes and
extracts the modified branch before comparing its early and
late slack under unchanged SDC. Its starting layout remains
outside the density range. The pilot will guide a legal hold
repair on an accepted-density layout if needed. Inputs, logs and
reports are under `work/history-btb-write-hold-pilot-20261118-r1/`.

The write-input pilot completed on the first banked checkpoint.
Twenty of the 30 inventoried write-address, enable, and reset inputs
had at least one negative early path. Six BUFX2 repeaters on
`write_pc_i[0]` improved its extracted CPPR hold slack from -185 ps
to +116 ps with the original constraints. Its worst write setup
slack decreased from +9,467 ps to +7,780 ps. This is a one-port
diagnostic on the 83.503% layout.

A fallback under `work/history-target-budget-20261118-r3/` waits
for the banked route to meet die utilization, DRC, and connectivity.
On a separate checkpoint it inventories all 30 write/control ports
and inserts root repeaters only on ports with negative early slack.
Chain sizing uses 35 ps per cell and aims for 50 ps of hold margin.
Extracted global timing, read-to-hit delay, die utilization, DRC,
and both signal and power connectivity are checked again after the
repair. The report classifier was replayed against all 30 pilot
reports. A coordinator startup with an unset module search path
failed before opening a checkpoint. The corrected launch and
`work/heldout-admission-20261118-r4/` are waiting for a qualified
physical producer. The locked workload outputs are still absent.

The first flat BTB reference route completed in 2 h 00 min.
Internal DRC, signal connectivity, and supply connectivity passed.
The final tool reports show +3,333 ps setup and -290 ps hold slack.
Placed cell area was 1,069,219.908 µm² on a 1,279,240.170 µm² die,
giving 83.582% utilization. The coordinator started a larger-die
retry. The first flat route remains outside the physical gate.
Inputs and reports are under
`work/history-btb-reference-route-20261118-r1/attempt1/`.

The second banked layout completed in 1 h 47 min. Internal DRC
and both connectivity checks passed. The final tool reports
show +4,033 ps setup and -291 ps hold slack. Placed cell area was
1,142,352.846 µm² on a 1,517,774.720 µm² die, giving 75.265%
utilization. This exceeds the predeclared limit by 0.265 percentage
points. The coordinator retained the result and started a third
floorplan. The fallback remains gated on the utilization range.
Reports are under `work/history-btb-reference-route-20261118-r2/attempt2/`.

The third banked floorplan and second flat floorplan again showed
69,632 negative early endpoints before automatic hold optimization.
The intermediate transforms inserted tens of thousands of cells
and still left a global violation above 290 ps. A separate banked
physical producer now applies the measured root-port repair after
post-route DRV repair in place of endpoint-by-endpoint hold
optimization. It retains the same netlist, I/O and clock constraints,
CTS, RC extraction, and final physical checks. Its 1,012 µm square
core is sized from the first run's 60.79% pre-hold core density.
The new placement can change either density or timing. It must pass
the same final gates under GPDK45. Inputs and outputs are isolated
under `work/history-btb-early-hold-route-20261118-r1/`.

The early repair producer now has an independent qualification
watcher under `work/history-target-budget-20261118-r4/`.
It requires completed CTS, extracted timing, final DRC and
connectivity, accepted die utilization, and a matched target-arrival
recheck. A single controller under `work/heldout-admission-20261118-r5/`
chooses the first fully qualified timing producer.

The third banked layout passed the 65–75% die utilization gate
at 71.868%. Placed cell area was 1,172,859.588 µm² on a
1,631,955.144 µm² die. Internal DRC, signal connectivity, and
supply connectivity passed. The unrestricted flow reports showed
+4,365 ps setup and -309 ps hold slack. The independent restored
CPPR recheck measured -148 ps hold and found negative slack on
nine of 30 write/control inputs. The fallback is repairing that
checkpoint in its own directory, `work/history-target-budget-20261118-r3/btb/`.
The area, timing, and checks on the repaired checkpoint are pending.

Both targeted write-port experiments completed. The repair of the
third banked checkpoint improved its global extracted CPPR hold
slack from -148 ps to +1 ps. Setup slack was +4,363 ps, read-to-hit
delay was 9,362 ps, and die utilization was 71.873%. Internal DRC
and both connectivity checks passed. Its wrapper initially matched
an echoed Tcl branch instead of the terminal output marker. The
preserved terminal marker and reports show the repair ran.

The independently placed banked version applied the root-port
repair during the physical flow. Its extracted CPPR setup and hold
slack were +5,147 and +41 ps, read-to-hit delay was 8,578 ps, and
die utilization was 69.821%. Placed cell area was 743,667.030 µm²
on a 1,065,106.560 µm² die. Internal DRC and both connectivity
checks passed. Its qualification retry recognizes the Innovus
checkpoint directory and preserves the first checker log. The
earlier repair has less hold margin and its read path exceeds
the current target budget. The 8,578 ps physical reference is
therefore being evaluated against both history arms before any
held-out run. See `work/history-btb-early-hold-route-20261118-r1/`
and `work/history-target-budget-20261118-r4/`.

The 8,578 ps BTB reference gives a 9,582 ps composed input arrival,
including 904 ps for the upstream address and 100 ps for the
separate layout boundary. The matched GPDK45 history STA passed at
13,850 ps. Recurrent/lease setup slack was +1,286/+189 ps, hold
slack +22/+3 ps, and target arrival slack +1,613/+330 ps. The
existing 80,001-edge directly annotated power replay uses this same
clock. The exact timed gem5 binary and frozen configuration passed
all 21 checksum cases and 11 cross-checks. Timing and checksum
evidence is under `work/history-target-budget-20261118-r4/` and
`work/heldout-admission-20261118-r5/`.

The held-out gate then opened the six clean references. Both arms
of Basicmath and Patricia aborted at the same musl `fmt_fp` store
past the mapped stack. Logs show unimplemented gem5 x87 `FSUBR` or
`FCOMIP`. Disassembly identifies the store in the common floating
point formatting loop. This is a shared clean execution failure.
The precise cause of the loop overflow remains under test. No
fault tape or runtime comparison has been admitted. A fresh gem5
build under `work/gem5-heldout-x87-build-20261118-r1/` tests the
missing decode paths using the existing gem5 x87 arithmetic and
compare model. The pinned workload files, original outputs and
SOURCE settings are preserved.

A standalone finite-double formatting probe reproduces the same
`fmt_fp` crash without an unimplemented-instruction warning. A
bounded limb probe produces identical wrong numerical intermediates
under AtomicSimpleCPU and O3. A focused x87 test clears the cause
of the zero integer limb. A regular load of 1.5 remains correct,
while `FLD ST(0)` pushes zero into an unused stack register and
a subsequent `FISTP` converts that zero. The generated
`FLD_R` inherited a four-byte operand size from the shared m32
decoder and `movfp` copied only the lower 32 bits of the internal
64-bit payload. The register copy must use the full internal
payload width. The x87 model still has its original double
precision approximation for stack arithmetic.

The initial build that added only `FSUBR` and `FCOMIP` was
stopped and its files retained. The separate repair build in
`work/gem5-heldout-x87-build-20261118-r2/` also forces a full
register copy for `FLD ST(i)`. The original failing probes are
under `work/gem5-heldout-x87-probes-20261118-r1/`. A fresh
gate in `work/heldout-admission-20261118-r7/` requires the
native-reference instruction and formatting probes, locked
file hashes, and a new exact-binary checksum before running
clean references again. The faulted phase remains gated on
the clean references. This is simulator compatibility work.
The workload binaries, protection policy and matched timing
constraints remain fixed.

Both original CRC32 clean cases passed exact stdout, retirement
and delivery validation. They retired 507,879,258 instructions
per arm and made no indirect conditional queries. The recurrent
case took 428,544,397 cycles and lease took 428,915,731 cycles
(+0.08665%). This is a clean observation on the original simulator
build. It is archived separately from any comparison made with
the compatibility build.

The second x87 build passed the duplication probe and matched
all printed limbs in the bounded numerical probe. It still failed
the arithmetic and full format gates. A reused-slot test identified
the same narrow-copy defect for constants and m32 loads. With 8.0
previously in the slot, `FLDZ`, `FLD1`, and an m32 load of 1.5
each returned 8.0. These paths also inherit a four-byte data size
at the generic move. The third build makes all x87 floating stack
copies full-width while leaving the memory operand widths intact.
Its admission gate checks reused-slot loads, register duplication,
arithmetic and comparison, formatted output, locked workload
hashes, and the exact timed checksum. Logs are under
`work/gem5-heldout-x87-build-20261118-r{2,3}/` and
`work/heldout-admission-20261118-r8/`.

The full-width x87 build passed all four probes, all 16 locked
artifact hashes, and the 21 timed checksum cases plus 11
cross-checks. The two Basicmath and two Patricia clean runs
completed with equal stdout within each arm pair. They failed the
locked host byte comparison. Basicmath differed on 9,905 of
19,733 lines. Patricia differed on 10,437 of 10,440 lines, all
in its printed input-time field; address and lookup-result fields
agreed on every line. The x87 model's double-precision arithmetic
remains a compatibility limitation for musl's extended-precision
conversions. No stdout criterion was changed.

The clean-qualified runner verifies the exact archive plan and six
clean records using the already tested binary and config hashes.
It independently admits only workload pairs with passing clean
stdout, execution contracts, and matching retirement identity. For
each admitted workload it retains the original eight owner seeds
and absolute SOURCE tape law. Ineligible workloads remain in the
admission and summary files as failed clean gates. It waits for the
original clean archive rather than rerunning any validated clean
work. The runner logs are in
`work/heldout-clean-qualified-20261118-r1/`.

The compatibility build also passed all 14 finite checksum cases
and the canonical source audit. CRC32's two clean records exactly
reproduced the original simulator's exit ticks, retirement count,
and stdout. Its clean lease cost is +0.08665% (+371,334 cycles)
at 13,850 ps per cycle. The patched CRC32 records were admitted
to the fixed eight paired SOURCE tapes. Sixteen faulted cases
are scheduled, with eight workers. Basicmath and Patricia remain
failed under the original exact stdout rule. The admitted plan
and results are in `heldout-source-20261118-r3/` under the
private experiment root.

A separate functional probe linked the same Basicmath and Patricia
sources against the server's glibc. Both candidate executables
produced the original locked output byte for byte on the x86-64
host and in gem5 AtomicSimpleCPU. This uses the same inputs and
provides a route for compatibility validation. It is a functional
probe with newly linked executables. No staged O3 comparison or
fault run has used those binaries. Artifacts and probe logs are
under `work/heldout-libc-compat-probe-20261118-r1/`.

All 16 faulted CRC32 cases completed. The mean benefit was
-0.048674% across eight comparable SOURCE pairs, with exploratory
95% owner-bootstrap interval [-0.049202%, -0.048091%].
The lease reduced mean incremental fault runtime from +0.038004%
to +0.0000468%. Its +0.086650% clean cost exceeded that saving.
The separate results note records every pair, coverage, costs,
and the unresolved exact stdout failures for Basicmath and Patricia.
See [the held-out report](../results/source-heldout-2026-11-18.md).

Two short host-versus-gem5 probes isolated the remaining x87
precision issue without reopening the frozen workloads. A C
probe for the rounding idiom used by musl formatting added 0.5
and 1.5 to a volatile long double at 2^64. With 1.5, the host
value changed while both AtomicSimpleCPU and the staged O3
simulator reported equality. The 0.5 control rounded away on
all three. A separate static musl probe emitted the binary32
results of decimal scanning using integer formatting. Three of
four inputs differed before any floating-point formatting. For
example, the host parsed 0.246373 as 0x3e7c4934, while gem5
returned 0x3e7c4800. This locates a Patricia-style discrepancy
at parsing and supports the precision explanation for the
Basicmath-style formatting discrepancy. The probes and raw
output are under `work/heldout-x87-precision-probe-20261118-r1/`.
Full native behavior for the existing binaries would need
extended-precision values carried through gem5's x87 stack
registers and arithmetic. There was no change to either locked
binary or the stdout gate.

The separate mismatch monitor now has an equal-budget C++
regression across every single raw and fold bit and every
starting probe phase. Persistent isolated discrepancies were
visible by probe seven in all 910 raw and 1,400 fold cases.
At the first probe, 304 raw and 200 fold cases were visible.
When the faulty raw value agreed with its canonical folds,
zero of 910 cases were visible. These are coherent component
snapshots. The experiment provides neither workload-specific
oracle input nor feedback to lease4096. See the
[online monitor note](ONLINE_MISMATCH_MONITOR.md). The C++
suite and all 70 Python tests passed.

The two optional glibc candidates are dynamically linked. Their
private compatibility manifest pins both executables, Patricia's
original input, both original stdout files, the ELF interpreter,
libc, and libm. All eight SHA-256 checks and both archived atomic
stdout comparisons passed. The manifest is under
`work/heldout-libc-compat-probe-20261118-r1/` and does not replace
the original benchmark lock.

A separate x87 prototype explores completing the original locked
executables with a correctly sized register representation.
It adds an independently renamed sign/exponent lane to each
x87 stack slot and connects both lanes to `FLD m80`, `FADDP`,
and `FSTP m80`. This tests an end-to-end load, arithmetic and
store dependency rather than only using extended arithmetic
inside a host-side helper. The prototype is intentionally
incompatible with the remaining x87 operations and is isolated
from all held-out runners. Its build and probe are under
`work/gem5-x87-extended-prototype-20261118-r1/`.

The native probe emits all ten payload bytes for 36 control and
rounding-boundary operations. The existing simulator completed
the probe and reproduced all 12 half-ULP control results. It
rounded away the 24 positive and negative 1.5 test offsets,
which should move the 2^64-magnitude result by one extended
ULP. The first atomic attempt reached its short simulation limit
before producing all records. The retry used the existing
longer diagnostic configuration and completed normally.

The extended stack prototype built successfully. Its atomic
probe returned incorrect ten-byte results even on the control
inputs, so the checker withheld O3 validation. The logs remain
isolated and the prototype did not enter the experiment build.

The user authorized a separate glibc follow-up for Basicmath
and Patricia. Its preflight verified the original artifact lock,
the two compatible executable hashes and shared library hashes,
and exact parity of input hashes, stdout hashes, seed order,
SOURCE law, paired-bootstrap settings, and execution limits.
Before running the follow-up, four clean cells and 32 faulted
cells were declared. The O3 runs use the same 13,850 ps composed
timing, measured service settings, and checksum-qualified binary
as the completed CRC32 comparison. Each workload must pass
both exact clean stdout checks and retirement identity checks
before its unchanged eight SOURCE pairs can start. Results will
report the two compatible variants as a follow-up cohort. The
original frozen failure records and CRC32 cohort remain intact.
The private producer is `work/heldout-glibc-followup-20261118-r1/`.

All four initial glibc clean runs failed with a duplicate pending
query owner. An O3 trace identified a `PSRLDQ` internal microcode
branch. Fetch treated control without the unconditional flag as
a conditional request. The BPU classified the same micro-op as
`NoBranch` because its conditional flag was unset, leaving the
reserved request unconsumed. The next request hit the duplicate
owner check. Fetch now uses the BPU's affirmative conditional
flag. The existing BPU history update and target behavior are
retained.

A freestanding `PSRLDQ` plus conditional-branch regression
prints the expected native result and reproduces the duplicate
owner error on the old staged binary. The C++ suite and all 70
Python unit tests passed. The new private build will run the
regular 14-case checksum, the native timed gate with the new
probe, compare prior checksum observations and activity traces
byte for byte, and confirm zero affected branch class lookups
in the existing CRC32 runs. The glibc follow-up retries with
the newly fingerprinted build only after those gates. The
initial logs are in `work/heldout-glibc-followup-20261118-r1/`.
The build and gates are in `work/gem5-frontend-owner-fix-20261118-r1/`.

The corrected front-end build passed the canonical source audit,
all 14 finite checksum cases, 23 native cases and 12 cross-checks.
The targeted native and staged `PSRLDQ` tests both passed and
retired the same stream. The original 21 native case observations
and all four bounded history activity traces matched the previous
qualified build exactly. CRC32's two clean and 16 faulted archives
contain zero `NoBranch` BPU lookups, so the fix's changed admission
condition was absent from their measured path. The original power
and CRC32 observations remain applicable to their own producers.

All four corrected glibc clean controls matched the locked host
stdout and their matched retirement identities. Basicmath retired
51,416,894 instructions per arm, using 57,639,766 recurrent and
57,671,810 lease cycles. Patricia retired 73,714,108 instructions
per arm, using 85,117,221 recurrent and 85,159,564 lease cycles.
Both pairs had zero indirect conditional lookups. The producer
opened exactly 16 paired SOURCE tapes for the two admitted
workloads with the original owner seed schedule. Results and
logs are under
`work/heldout-glibc-followup-20261118-r1/evaluation-owner-fix/`.
