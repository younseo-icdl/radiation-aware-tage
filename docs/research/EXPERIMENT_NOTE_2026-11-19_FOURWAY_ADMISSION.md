# Four-method native TAGE admission

This study compares ordinary recurrent TAGE, Lease4096, SECDED halt,
and TMR on one native O3 path. SECDED with committed fallback and
refill is a separate required comparison. The controlled CPU track
keeps the 13,850-tick model clock, staged hash and row timing, training
port and owner contract fixed. Hardware qualification is a separate
track. The previous 500-tick finite-model runs and their protected
source transport remain a separate historical result.

## Recovered baseline

The received handoff manifest verified all 1,394 covered files. The
archived analyzer regenerated all 102 matched pairs byte-for-byte
from 204 run records. The handoff's 23 synthetic analysis tests
passed. The new tape reader regenerated all 48 previously archived
non-anchor variable-rate tapes with their exact schedules and verified
the original digests. These used the fixed 500 ps grid, 205:9
multiplicity and contiguous raw130 logical ages.

The six live workload asset sets, two gem5 executable hashes and
shared producer config hash matched the recorded run plans. The raw
asset and resolved configuration fingerprints are in
`work/fourway-20261119.B5Hhgo/baseline/provenance.json`.
The pinned upstream source was c8222cc67a399bfc01e8658dd14b30d5bfd634f9.
Two separate historical binaries produced the earlier results. The
CRC32 archive used a different producer from the other five workloads.
The new matched study will include fresh correctness checks on all
six workload asset sets.

Four selected SHA-1 runs re-executed using the original executable,
configuration, retired instruction stream and shared tape. Both clean
arms and the first 2,000 events/s pair matched archived exit ticks,
provider counts, applied events, and lease publication counts.
The earlier finite checksum regression also passed all 14 cases.

| Workload | Archived paired benefit at 2,000 events/s | Ordinary mean direction MPKI | Lease mean direction MPKI |
|---|---:|---:|---:|
| Quicksort | +17.43222% | 35.09460 | 7.37458 |
| Dijkstra | +0.46313% | 1.66649 | 1.15047 |
| SHA-1 | +2.15731% | 2.45907 | 0.26592 |
| Basicmath | +4.15967% | 7.29387 | 1.36436 |
| Patricia | +5.17996% | 9.59619 | 1.26877 |
| CRC32 | −0.04867% | 0.08042 | 0.05165 |

Each row uses the eight archived schedules for that workload. Neither
the original nor reproduced observations contain native ECC or TMR.

## Native controlled integration

The stored active history is 23 words and 346 payload bits. The
ECC halt prototype pairs those words with 121 stored check bits.
A terminal DUE prevents writeback of all candidate repairs at that
boundary and requests a typed simulator stop. The TMR prototype
keeps two additional persistent copies of the active words. It
votes bitwise on the actual copies and publishes repairs to
divergent storage. A dedicated PCG64 replica stream maps each
primary tape event to one replica, maintaining event multiplicity
and the absolute logical time. Directed two-replica cases are
outside that ordinary mapping.

Branch outcomes and retired direction statistics come from the real O3 commit
path. The exporter checks TAGE provider totals against committed
conditional updates and retired instructions against the simulator
counter. It retains partial observations at detected stop without
creating a completion time.

Protection runs before a pending hash is captured or a CPU edge
consumes state. Legitimate speculative append/restore operations
update check bits or replica state. The CPU model treats
correction or voting at this boundary as combinational and writes
repairs back on the same boundary. The dirty flag avoids redundant
host-side computation when no injector has invalidated storage.
These assumptions establish the controlled equal-latency contract
only. The model's scope is the active word set. Neither the
inactive raw ring nor saved path checkpoints are newly protected
by this model.

All 13 initial directed O3 cases passed. The two SECDED stop
cases halted at tick 512,450. The ECC-halt and TMR clean runs
matched ordinary TAGE at 1,529,538,600 ticks and 233,030 retired
instructions. A fault at the exact first hash-capture tick
was repaired before hashing in both variants. The raw outcomes
are in `work/fourway-20261119.B5Hhgo/directed-native/DIRECTED.json`.
The initial gate also checked post-exit censoring.

A second native producer implements ECC+refill. It drains the old
owners and pending query before resetting selected history, suppresses
speculative history writes during bimodal fallback, and publishes from
committed branch outcomes through a one-reservation-per-cycle port.
After the first 130 committed appends, admission closes and the
fallback owners drain before tagged lookup resumes. Branches already
in flight may publish during that last drain.

All 16 native scenarios passed, including both deliberate ECC halt
outcomes and two refill cases. The refill cases each restarted once,
matched the checksum and the 233,030 retired-instruction baseline,
and published 131 committed updates with 131 reservations. One case
injected DUE at the pending-hash capture tick and verified recovery
after cancellation. The complete second gate is in
`work/fourway-20261119.B5Hhgo/directed-refill/DIRECTED.json`.

## Campaign order

1. Pass native directed checks and clean equivalence in all five
   configurations. Reconcile selected native ordinary/rebuilding
   results against the historical results using actual output,
   completion, provider counts and runtime configuration.
2. Run the three-workload pilot with four new seeds per faulted
   cell and independent confirmatory seeds. Set the final
   precision and run count after observing pilot variance,
   correct runtime pairs, and execution cost.
3. Run the frozen confirmatory plan and separate single-bit
   diagnostic. Preserve stop, timeout and silent corruption
   observations with the applied tape prefix.
4. Measure matched GPDK45 post-route behavior, then evaluate
   a timing-qualified CPU comparison. Keep clean and faulted
   power windows separate. Complete the footprint, interval
   and causal follow-ups before final figures and the handoff.

## TMR hardware admission

The staged history wrapper now has a TMR mode with the common
1,024-bit raw ring plus two 130-bit active-raw copies. It also
duplicates the 200 folded bits and 16 path bits twice. The
majority signal is forwarded through undo, and source writeback
maps any primary raw corrections back to their ring rows.
Speculative path checkpoints, head, and query storage remain
common. The two 346-bit redundant copies are active storage,
before counting the rest of the block.

Xcelium passed directed read, append/undo, cross-domain repair
and wrong-majority writeback tests for TMR. The existing SECDED
RTL regression also passed. Genus synthesis started from the
same 13.850 ns staged history boundary with equivalent-flop
merging disabled. A netlist must retain 346 flops for each
additional copy before it can enter P&R. Apply the same
retention policy to all fresh mapped controls. TMR timing,
cell area, and power remain to be measured.

## Pilot launch

The final native producer passed the source-overlay and pinned x87
compatibility audit. Its finite checksum suite passed all 14 cases.
Four additional native SHA-1 re-executions on this producer matched
the older ordinary/rebuilding exit ticks and direction counters under
the original clean and 2,000 events/s conditions. They remain outside
the pilot. The checked producer is commit db8b866. The binary hash
and source audit are recorded in the private run namespace.

The pilot launched in `fourway-pilot-20261119-r1` with up to 16
gem5 processes. It admits the faulted cells only after all 15 clean
workload/method combinations validate. The planned budget is 195
runs including those clean controls. The proposed confirmatory seeds
were checked to be disjoint. Confirmatory precision and replicate
counts still depend on the observed pilot. No rate result is inferred
from a planned cell.

The hardware flow now has separate ordinary and TMR mapping jobs.
The matching Lease4096 and SECDED halt synthesis runs are queued with
the same flop-retention policy. The audited TMR declaration is 10,328
bits, including the common 9,636 bits and two 346-bit replica sets.
The audit records declared RTL bits separately from mapped flops
and placed area.

## ECC+refill hardware admission

The staged ECC refill build adds committed direction/path valid and
ready handshakes. A DUE cancels the query packet and blocks new
admissions. The enclosing owner-drain signal authorizes the reset,
and the fallback variant uses the base provider while collecting
130 committed history bits. Speculative fallback responses do not
modify the protected history or path checkpoints. After refill, the
controller waits for the remaining fallback owners before re-enabling
the tagged provider. The companion processor supplies committed
outcomes and authentic owner-drain state. The history block includes
the ingress gate, recovery controller, and base-provider mask.

The standalone Xcelium test exercised a repeated DUE before re-entry.
The integrated test verified a real double-bit error at the history
storage, pending-packet cancellation, bimodal fallback, 130 committed
writes, and the final drain before tagged re-entry. The existing
non-refill pipeline regression also passed. The variant declares
11 recovery controller bits in addition to the halt-mode history
RTL. Mapped storage, routing and activity values are pending. The
new synthesis variant is queued with its own build records.

## Common clean activity qualification

All five RTL configurations replayed the same clean Xcelium input
trace for 80,001 edges, 14,519 verified row responses, and one
cancellation. The Lease4096 variant published four times. The
other variants used identical idle input cycles at those edges.
The replay records are in
`fourway-rtl-20261119-r1/clean-replay-rtl/` on the simulation volume.
These are RTL functional checks. Routed activity and power require
the separate gate.

The physical queue uses fresh GPDK45 floorplans after all five
synthesis producers qualify. Its default is a common die area
when the measured cells admit a shared 65–75% utilization range.
The fallback uses the same target utilization with separate die
areas, which are recorded per arm. It checks internal DRC,
connectivity and TMR register retention after route. The extracted
timing recheck uses common row and target-arrival bounds and CPPR.
The clean power step uses the qualified shared clock and requires
complete flop-output and net activity annotation.

## Fixed per-bit tape admission

The native catalog tool constructs a semantic union from the run
manifests and drives a K1 Poisson stream at the requested intensity
per union site. Each arm receives the subset of events that hit a
present site, at the same original absolute tick. This gives each
exposed site the same marginal intensity and each arm the expected
event rate of intensity times catalog size. Coincident timestamp
records remain distinct. There is no assumed physical adjacency.
The tool preserves union, per-arm and manifest hashes and audits
the exact applied prefix, storage IDs, XOR values and censored tail.

The directed checksum run used five real manifests and reached
all added storage classes that this catalog exposes. It verified
17, 18, 25, 52 and 25 injected events in ordinary, Lease4096,
SECDED halt, TMR and SECDED refill, respectively. The Lease4096
run included two age-counter flips, each SECDED arm included
nine check-bit flips, and TMR included 36 replica flips. All
five programs completed correctly. This is a tape and delivery
test and does not estimate workload performance.

The current native follow-up catalog contains 346, 359, 467,
1,038 and 467 sites in the same order. The exact scopes are
active history, supported check and replica storage, and the
lease age counter. Timer, stop-latch and refill-controller
fault interfaces are still needed for broader control exposure.
Inactive ring state, checkpoints and pending query state also
require separate mapping. The current catalog must not be used
as a whole-history-block physical fault inventory. The private
admission logs are under `work/fourway-20261119.B5Hhgo/catalog-smoke.X0N9AK/`.

## Faulted activity fixture

A separate 5,213-edge history-block fixture supplies the same inputs
with zero, one, or two raw bit flips. The cells are logical ages three
and four in the primary copy after eight warmup appends. They are
consecutive ring addresses. The fixture makes no placement-adjacency
assumption. For the routed arm, the upset reaches the actual primary
storage output before the clock edge. The test verifies the stored
result after releasing the forced value and compares subsequent
control, indices, tags, and prediction outputs with the RTL arm.

All 15 RTL mode and fault-width combinations passed. All six
cross-checks against the two previously routed Lease4096 and SECDED
halt checkpoints also passed. In the two-bit test, SECDED halt
accepted no responses after the fault. SECDED refill resumed and
accepted 633 responses. TMR accepted 650 and repaired the primary
raw state. Lease4096 accepted 649 and published once. These directed
results exercise the recovery paths and are separate from workload
accuracy measurements.

After the new physical and clean-power gates pass, the power
queue replays this fixture for all five new routed arms at the
qualified shared clock. It saves matched fixed-window K0, K1, and
K2 energy, observed response counts, and stopped edges. Energy
measured after a halt describes the block during the observation
window. Correct application completion is a separate CPU result.

## Confirmation planning gate

The sweep-design tool validates the entire declared pilot before
producing a precision projection. Runtime and MPKI projections
use only the seeds on which both compared arms completed correctly.
A missing joint success or insufficient variability evidence
leaves the projected width unavailable. The report also reads
observed host time from terminal gem5 statistics and scopes the
cost projection to the workloads and rates observed in the pilot.

The tool can freeze an independent 8, 16, 32, or 64-seed grid after
the precision targets and budget rationale have been recorded. The
eight-seed setting reproduces all 990 rows of the proposed primary
plan exactly. Expansion preserves those proposed seeds and uses
disjoint ranges for further seeds, rates and fault laws. Both fault
laws share a single declared clean control per workload and mode.
No confirmatory budget has been selected from partial pilot data.

The freeze ledger records the SHA-256 digests of both the pilot results
and the emitted confirmation grid. Before starting the matched-clock
campaign, the runner checks those digests, verifies seed independence,
rechecks simulator and workload provenance, and runs clean admission
before scheduling faulted pairs. The proposed primary grid passed a
structural dry run with 990 rows and 192 distinct fault seeds.

SciPy 1.18.1 was installed in the project environment with the
existing NumPy 2.5.5. The handoff's BCa helper generated a finite
pointwise interval on a nondegenerate eight-pair test input.

## Clean pilot and lease fetch accounting

All 15 clean controls completed correctly. For each workload, both
SECDED modes and TMR matched unprotected TAGE in completion tick,
retired instructions and committed direction counts. The 180
scheduled faulted runs were then admitted with at most 16 jobs.
Detected stops from SECDED halt are valid reliability outcomes.

The native configured run uses one thread and one fetch attempt per
cycle. The lease-gating check happens after the fetch cache and
interrupt early returns and before the instruction fetch loop. A
blocked check takes either the restore-owner drain branch or the
quiescent service branch. The two counts partition the blocked
fetch opportunities. The service CSV independently records start,
publication and any in-flight interval censored at architectural exit.

`python -m simulation.analysis.lease_stalls RUN_ROOT UNPROTECTED_RECORD LEASE_RECORD`
rechecks the run configuration hashes, stdout, terminal statistics and
lease event ledger. It emits the conditional paired direction and time
deltas and the exclusive fetch counts. In the clean pilot:

| Workload | Lease minus unprotected cycles | Direction misses delta | Direction MPKI delta | Drain fetch cycles | Service fetch cycles |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quicksort | +37,380 | +418 | +0.01647 | 28,771 | 5,206 |
| SHA-1 | −1,575 | 0 | 0 | 9,736 | 402 |
| CRC32 | +371,334 | 0 | 0 | 299,836 | 65,350 |

CRC32's clean completion cost was 0.087% with unchanged committed
direction outcomes. The 365,186 blocked fetch cycles show how often
maintenance denied a fetch opportunity. The CPU backend can continue
during these cycles, and shifting fetch can change the timing of other
events. SHA-1 finished 1,575 cycles earlier despite 10,138 blocked fetch
cycles, illustrating why subtracting the blocked count from completion
cycles does not identify a residual causal effect. Faulted pairs and
fold-residue lifetimes require separate evidence.

## Physical storage inventory and exposure scope

`simulation.eda.storage_inventory` enumerates the sequential instances
in each Genus netlist using the Liberty flop definitions and reconciles
the total mapped cell count with the Genus top-level area report. It
records separate RTL declaration counts, synthesized FF counts,
and the logical fault catalog that the native simulator actually
accepts. The optional mapped register CSV keeps each instance and
storage category inspectable.

The first two new matched GPDK45 netlists contain 9,636 FFs for
unprotected TAGE and 10,328 FFs for TMR. Both include a 1,024-bit
physical raw ring, 10-bit head, 200 fold bits, 16 path bits, 8,192
checkpoint bits, and 194 query-packet bits. TMR adds 692 FFs for
two separately stored replicas of the 346-bit active payload. In the
native simulator, those two arms expose 346 and 1,038 bits
respectively, because the native catalog covers the active raw
window and recurrent folds/path plus the two TMR replicas.

The earlier Lease4096 and halt-only SECDED netlists also served as
parser regression inputs. They contain 15 lease-control FFs (13 age
and 2 service timer) and 122 SECDED FFs (121 check and one sticky
failure), respectively. Of those, the current native catalog can
inject the 13 lease-age bits and 121 SECDED check bits. The timer,
sticky failure, refill controller, retained raw storage, head,
checkpoints and query packet require separate mapping before a
full physical-inventory exposure claim. The earlier netlists are
separate from the new routed comparison.

The Xcelium RTL fixture in
`tests/rtl/history_control_upsets_tb.sv` also exercised direct
storage upsets through `simulation/eda/storage_xor.c`. The VPI
function deposits an XOR into one selected bit, reads it back
immediately, and leaves the HDL process responsible for the next
edge. It rejects an unknown or inaccessible bit. The three fixture
elaborations checked both values of each declared protection
control bit. The SECDED sticky failure was checked in both policy
arms.

| RTL arm | Directed result |
| --- | --- |
| Lease4096 | Setting the age MSB triggered drain with a live owner. Flipping the running timer from 2 to 3 delayed publication by one edge. |
| SECDED halt | Setting the sticky failure bit blocked new queries and the halt persisted until reset. |
| SECDED refill | The sticky failure initiated refill. Flipping the remaining count from 130 to 2 reduced the refill to two committed writes before fallback drain. |

The 64-bit Xcelium build ran at a 13,850 ps simulation period in
each fixture. These tests establish delivery and directed block
behavior in RTL. They do not change the fixed per-bit CPU exposure
catalog or establish hardware timing.

To reproduce, compile `storage_xor.c` as a shared library using
the simulator's VPI headers. Run Xcelium with `-sv -access +rwc
-loadvpi STORAGE_XOR_SO:register_storage_xor -top
history_control_upsets_tb` and the history pipeline, state, hash,
provider, lease, SECDED and refill RTL sources. The default
elaboration selects Lease4096. Set the testbench parameters
`LEASE_PERIOD=0` and `SECDED=1` with `-defparam` for halt, and
also define `TAGE_HISTORY_REFILL` for refill.

### Fixed per-bit RTL binding and delivery check

`simulation.eda.rtl_storage_catalog` emits one binding per declared
storage bit at the exact history-pipeline boundary. A probe first
initializes the unreset path checkpoints and query-packet registers
through ordinary inputs, then flips and restores every listed bit
at RTL. Xcelium verified 9,636 bindings for unprotected, 9,651
for Lease4096, 9,758 for SECDED halt, 9,769 for SECDED refill and
10,328 for TMR. The physical raw-ring address and bank-local
replica/check address are stable despite the current history head.

`simulation.eda.rtl_storage_tape generate` generates the union of
physical bit keys at common per-bit K1 intensity and filters it for
each variant. The declared 500 ps arrival grid is independent of the
13,850 ps RTL period. Different K1 records on the same tick are
delivered and checked separately. The matched Xcelium fixture passed
five clean and five faulted replays of 8,192 edges each. The
accelerated delivery-check intensity was 150 flips per bit-second
and the shared seed was 20261119071. Exact timestamp, storage
identity and read-back audits verified respectively 155, 155, 156,
156 and 168 fault deliveries in the same arm order. The fixed
synthetic transactions exercise block responses. Workload MPKI,
completion time, control-field exposure in gem5 and any physical
chip upset rate require other evidence.

For replay, generate the tape with
`python -m simulation.eda.rtl_storage_tape generate OUTPUT --seed
20261119071 --horizon-ps 113459200 --intensity 150`. Use the
previous Xcelium top and options with `+storage_tape=ARM_TAPE` and
`+storage_edges=8192`. For unprotected set `LEASE_PERIOD=0` and
for TMR set `LEASE_PERIOD=0` and `TMR=1`. Use `+storage_catalog=CATALOG`
for the independent binding check. Audit each transcript with
`python -m simulation.eda.rtl_storage_tape audit ARM_TAPE CONSOLE_LOG`.

## Matched physical scheduling

The halt-only SECDED synthesis started in the second 16-CPU EDA
slot while Lease4096 synthesis was still running. The early Innovus
queue takes the Lease slot when that synthesis finishes. It attempts
unprotected, TMR, and Lease4096 on the same core dimensions and
constraints as the previous qualified Lease/SECDED common die,
while the halt and refill synthesis queue uses the other slot.

The early routes are eligible for the first matched physical attempt
only after the producer, mapped-netlist identity, site contract,
connectivity, DRC, and 65–75% final utilization checks pass. This
allows them to be reused with halt and refill routes on the same die.
If the first common die fails the geometry gates, the next attempt
uses measured placed area to size its floorplans. Common-clock
selection requires extracted global setup and hold to pass across all
five routes. The separate no-undo query report is diagnostic.

## Connecting extracted timing to gem5

`simulation.analysis.physical_clock` checks all five selected routed
checkpoints, their synthesis parameters, their geometry reports,
the applied SDC and CPPR setting, and the original extracted timing
reports. It requires nonnegative combined setup and hold and the
address-launch, provider and taken-target-valid setup checks. The
result binds the common period to the staged two-cycle query and
two-cycle lease service. It also records the assumed external row
and target arrival times. This qualifies the history subsystem under
those arrivals. CPU-wide implementation timing is outside this evidence.

The confirmation runner supports a separate implemented-clock cohort
after this gate. With a changed period it retains the frozen workload,
event rate, law and seed pairing, gives the runs fresh IDs, reruns
clean admission, and preserves the absolute-time source tape prefix.
Its observation bounds are scaled in whole reference-grid intervals
to retain at least the original cycle budget. If the extracted clock
equals the controlled clock, a complete matching run ledger can be
referenced by hash without repeating the simulations.

The existing 14,900 ps Lease4096 and halt-only SECDED reports passed
the single-arm evidence checks. The verifier rejected the halt reports
as a substitute for the refill implementation. A dry run projected all
990 candidate rows to the alternate period with unchanged seeds and
rates. This did not select a physical clock for the new five-arm study.

## Lease interval follow-up

The predeclared interval grid is disabled, 1,024, 2,048, 4,096,
8,192 and 16,384 accepted raw appends. Quicksort and CRC32 were
selected before their faulted pilot comparison was complete. They
represent the two workloads named for the handoff's causal comparison.
The follow-up uses clean controls and the confirmatory seeds at
2,000 events/s under the primary SOURCE law. This limits the
ablation to one nonzero rate while keeping all six required periods.

The disabled and 4,096 arms refer to the corresponding frozen main
results by provenance. The four new arms per cell use the exact same
fault tape, checksum and timing producer. The eight-seed proposed
grid gives 18 six-arm pairs with 36 references and 72 new runs.
The actual count follows the frozen main design's seed budget.
The interval runner requires the completed controlled cohort and
new clean gates before starting faulted runs.

`simulation.analysis.lease_intervals` verifies clean/faulted timing
and input provenance and the six-way tape pairing. It reports
completion counts and the joint-correct elapsed-time, cycle and
direction MPKI deltas against disabled, along with each arm's
degradation from its own clean baseline. Failures remain in the
completion denominator. The grid passed a structural dry run. No
interval outcome has been produced by the follow-up.

## Recovery and unequal terminal exposure

`simulation.analysis.protection_evidence` verifies completed
five-arm records against the actual program output, terminal
direction statistics, native configuration and delivered XOR
trace. It recovers logical ages from each arm's manifest and
counts K1 and K2 events and TMR replica placements separately.
It checks that all arms observed prefixes of the same logical
tape and reports the common prefix through the earliest stop
and the later events each continuing arm received.

For pilot CRC32 pair `planned-1493841e96a55462` at 8,000
events/s, SECDED halt stopped after 47 events and recorded one
uncorrectable word. Other arms completed with verified stdout
after 47,421 to 47,449 events. SECDED refill completed after
47,448 events, with 1,953 refill resets and 1,951 completed
refill episodes. The counts are per observed word or protocol
action, so a refill count need not equal a K2 count. The pilot
example demonstrates unequal terminal exposure and recovery
behavior under a shared tape. The study compares correct
completion rates and assigns no completion time to a detected
stop.

## Figure verification

The private handoff figure producer reads the native ledger through
the handoff analysis validator. The three-panel plot uses committed
direction accuracy, direction MPKI, and verified completion time with
a secondary cycle scale at a common clock. It shows per-seed points,
means and each arm's own clean level. A separate completion figure
keeps detected stops in the denominator and uses pointwise Wilson
intervals. The direct Lease4096 comparisons use jointly correct
seeds for the time and MPKI deltas, showing pointwise BCa intervals
only when estimable. Overlapping series use distinct marker shapes
and line styles at the original coordinates.

The initial render used the CRC32 pairs present in the pilot snapshot
and carries a partial-pilot label. Unmeasured cells produced no
points. The complete-render path rejected the partial snapshot against
the full declared plan. Figure exports include PNG, SVG, seed CSV,
paired effects CSV and input/plan hashes. A worker is queued to render
the complete pilot after its final run ledger appears.

## Physical comparison table admission

The power verifier checks the selected route, retimed SDC, reported
VCD window, slow power view, 0.9 V supply and 100% flop-output and net
activity annotation. It reads internal, switching, leakage and total
power in mW, checks their sum, and derives observation energy from
the reported interval. The existing reset-qualified Lease4096 and
halt-only SECDED reports passed these checks as regression inputs.

The matched table producer additionally binds each storage inventory
to the selected route's synthesis netlist. It joins the qualified
clock, placed cell area, state counts and power by the exact native
method configuration ID. Long clean replay and the equal-window K0,
K1 and K2 incidents produce distinct rows. A stopped block's incident
energy remains an observation-window quantity. Application completion,
performance and reliability come from the separate CPU measurements.
The table producer is queued behind the routed power measurements.

## Raw routed layout images

The handoff capture restores each selected Innovus checkpoint in a
fresh output directory. It exports three separate 2,600 × 2,600 PNGs
with the native viewer, consisting of a full routed view, a
placement-focused view and a 92 µm-square detail at the measured die
center. It records the die and detail bounds, routed netlist hash,
route producer hash and image hashes. The capture does not modify
the source checkpoints.

The existing halt-only SECDED route produced three distinct,
nonblank PNGs as a capture regression. The new five-arm image export
uses the selected matched routes only. The first matched Innovus
producer, unprotected TAGE, has started on the common die.

## Handoff archive verification

The local archive builder uses an explicit member list and records a
SHA-256 digest and byte count per file. It verifies the archived
contents before publishing the ZIP, with separate plan and observed
ledgers. The partial-pilot packaging check included 373 verified
members. Its contents include tracked source and implementation
patches, pilot statistics/stdout, terminal records and fault tapes,
baseline reproduction evidence, the analysis scripts and the preview
figures. A fresh extraction regenerated both the seed and paired
figure CSVs byte for byte. The package excludes Cadence libraries,
checkpoints and benchmark input distributions. This packaging check
is separate from the final comparison handoff.

## Quicksort and CRC32 causal replay selection

The workload residue replay selects the smallest locked numeric seed
for each named workload at 2,000 events/s under the primary SOURCE law.
It uses the unprotected and Lease4096 arms of that pair and the exact
archived tape. The observation window starts at the first scheduled
event and spans at most 2 ms. The terminal outcome and applied-event
prefix are checked against the original controlled run. If the pair
does not share exposure to the first event, the trace is unavailable
for that seed. No replacement seed is selected after outcomes.

The observer runs only after the directed trace-on/trace-off gates
and all 14 checksum regression cases have passed with its binary.
The follow-up combines the bounded per-bank residue observations
with prediction deltas and the exclusive drain/service counts
from the original comparison. Its seed selection passed a dry run
against the proposed grid. Actual residue measurements await the
frozen controlled run ledger.

## Presentation preservation check

The supplied editable deck and PDF each contain 95 pages in the
declared presentation order. The local update tool resolves the
PPTX slide relationships so it can replace a measured evidence
page and its speaker notes in place. Both formats receive the same
source PNG. Untouched PPTX parts, including charts and workbooks,
are checked byte for byte. The internal single-page trial rendered
six unchanged PDF pages identically, including the architecture,
routed-layout and earlier comparison pages. Both trial outputs
preserved the 95-page order.

PyMuPDF 1.28.2 was installed in a private presentation dependency
directory for the PDF update and render check. The trial used a
marked partial-pilot figure to verify the update path. Final
presentation content depends on the completed run and routed
evidence.

## Identical clean controls are reused

The matched-clock confirmation runner can now reuse the completed
pilot clean observations. It rechecks each original terminal status,
stdout digest, retired and direction counts, zero event delivery,
clock, protection interval and configuration digest. Reference rows
retain their measured run ID and point to the original record digest.
The planned cell ID and measurement role are recorded independently.
The same observation can also support both fault-law comparisons.

The actual pilot files qualified all 15 clean observations across
Quicksort, SHA-1, and CRC32. The proposed 30 clean confirmation
cells therefore require 15 new runs for the three other workloads.
A separate implemented-clock cohort with a different period still
requires fresh clean observations.

## Confirmatory precision and host budget

The planning report now lists the paired endpoints that meet a
proposed precision target at 8, 16, 32 and 64 seeds, alongside the
projected host hours for the workload and rate cells actually
observed by the pilot. It distinguishes wide estimates, low
projected joint completion and endpoints with insufficient pilot
variability evidence. A budget summary for planning targets of
0.1 percentage point in paired runtime reduction and 0.05
direction MPKI is queued behind the complete pilot. The suggested
seed count applies only to estimable pilot endpoints. The jointly
correct performance analysis, all-seed completion analysis and
frozen run selection remain separate.

## First common-die route observation

The unprotected Innovus route completed on the common 317,498.436 µm²
die. It occupied 219,765.438 µm² of placed cell area, or 69.218%
die utilization. The internal DRC, signal-connectivity and
power/ground-connectivity checks passed. This route is eligible
for the matched geometry comparison.

At the 13,850 ps period, standalone extracted STA using CPPR for
both edges and the shared row/target arrival constraints observed
global setup slack of −17 ps and hold slack of +19 ps. The worst
setup report went to the raw ring write path. This first routed
arm did not qualify at that period. The next period is being
checked, and common clock selection still requires the other
four implementations.

The 14,900 ps extracted check for unprotected TAGE passed with
+620 ps setup and +19 ps hold slack at the same external arrivals.
This qualifies the unprotected history subsystem at 67.11 MHz.
The matched run will reuse this STA evidence only when it selects
the same routed checkpoint and applied constraint set.

The first routed TMR attempt occupied 228,084.246 µm² on the
same die, or 71.838% utilization. Signal and power/ground
connectivity passed. DRC found one Metal1 parallel-run spacing
violation. The route is retained as a failed geometry attempt.
A localized routing ECO is queued from a separate copy of its
checkpoint. The repair must pass fresh DRC, connectivity, area
and timing checks before entering the matched comparison.

## Pilot closed and primary confirmation frozen

All 195 planned pilot executions have terminal evidence. Across
clean and faulted conditions, unprotected TAGE, Lease4096, SECDED
refill and TMR each completed 39 runs with matching stdout.
SECDED halt had nine correct completions and 30 detected stops.
The 15 clean controls passed. These are pilot counts across the
declared three workloads and rates. The primary-law TMR events
select only one replica per event.

The pilot used 32.08 summed gem5 host hours. For the pilot-overlap
cells, planning projects 61.7, 120.8, 239.1 and 475.8 host hours
at 8, 16, 32 and 64 seeds. The 16-seed plan meets the planning
targets for 47 of 55 estimable endpoints and avoids projected
joint-completion shortages in that set. The 8-seed plan meets
40 targets, while 32 seeds meet 49. The 64-seed plan still misses
five. Seventeen endpoints lack pilot variability estimates.

The primary law now has 16 independent seeds per rate and workload,
with 1,950 planned cells across all six workloads. Fifteen clean
cells reference the original pilot executions, leaving 1,935 fresh
runs. The seed budget was frozen uniformly before confirmation.
The separate K1 diagnostic and implemented-clock cohort are
independent of this ledger. The primary runner was admitted and
queued behind the bounded observer checksum regression so the
aggregate gem5 process count stays within 16.

The separate routing ECO cleared the single Metal1 spacing
violation on TMR with the same 71.838% die utilization and clean
signal and power/ground connectivity. The first Lease4096 route
passed the geometry checks at 70.152% utilization. Extracted
timing at the common candidate clock is in progress.

## Pilot direction and fetch accounting across all paired seeds

The completed pilot supplies 39 unprotected/Lease4096 pairs,
including three clean controls. The audit checked terminal
direction statistics and the lease service ledger for every pair.
The clean unprotected direction MPKI was 6.948 on Quicksort,
0.031 on SHA-1, and 0.052 on CRC32. CRC32 executed 80.1 million
conditional branches but recorded only 26,216 direction misses
in its clean run. Quicksort recorded 176,321 in 6.84 million.

The table gives means of four paired seeds at 2,000 events/s.
The signed differences are Lease4096 minus unprotected TAGE.

| Workload | Direction misses | Completion cycles | Drain fetch cycles | Service fetch cycles | Blocked fetch opportunities / unprotected cycles |
| --- | ---: | ---: | ---: | ---: | ---: |
| Quicksort | −697,439 | −6,819,189 | 28,934 | 5,226 | 0.087% |
| CRC32 | −14,548 | +209,871 | 300,007 | 65,350 | 0.085% |
| SHA-1 | −25,245 | −141,911 | 9,466 | 404 | 0.152% |

The similar normalized maintenance burden of Quicksort and CRC32
at this rate coincides with very different direction-miss changes.
CRC32's paired runtime reduction was −0.082%, −0.049%, and
−0.020% at 20, 2,000, and 8,000 events/s even as its direction
MPKI improved at all three rates. These observations support
different prediction benefits rather than different normalized
maintenance burdens as a promising explanation. The fetch blocks
can overlap useful backend work. The measurements do not assign
an exact cycle cost to each miss or identify specific damaged
branches. The four-seed pilot remains descriptive.

All 30 primary confirmation clean observations have verified
stdout. The 15 newly run cells cover Basicmath, Patricia and
Dijkstra, and the faulted primary phase has started. At 14,900 ps,
the qualified Lease4096 standalone check passed with +1,109 ps
setup and +19 ps hold, and the repaired TMR check passed with
+919 ps setup and +2 ps hold. The halt-only SECDED route was
started in the available EDA slot while refill synthesis continued.

## Separate single-bit diagnostic

The K1-only diagnostic is frozen at 2,000 events/s for all six
workloads, with eight independent paired seeds per workload.
This common rate supports direct comparison with the corresponding
primary-law cell while retaining the two exposure laws separately.
The grid contains 240 new faulted executions and 30 references to
the original clean measurements. The seed namespace was checked
against both the pilot and primary grids. No full four-rate K1
sweep is claimed.

The diagnostic, lease interval ablation and bounded workload
causality replay were queued behind the primary comparison and
will run in sequence. The K1 and interval producers use at most
16 jobs. The residue binary has passed the on/off equivalence
check and all 14 checksum cases.

## First four common-die geometries

All four rows below passed internal DRC, signal connectivity,
power/ground connectivity and the 65–75% utilization gate on the
same 317,498.436 µm² die. The TMR row uses the repaired route.

| Protection | Placed cell area (µm²) | Die utilization |
| --- | ---: | ---: |
| Unprotected TAGE | 219,765.438 | 69.218% |
| Lease4096 | 222,730.920 | 70.152% |
| SECDED halt | 227,828.088 | 71.757% |
| TMR | 228,084.246 | 71.838% |

Lease4096 uses 1.35% more placed area than unprotected TAGE and
2.24% and 2.35% less than SECDED halt and TMR, respectively, in
these early routes. All rows include the common ring, path
checkpoints and query packet. SECDED refill remains in synthesis.
The halt route's 14,900 ps extracted recheck and raw Innovus image
exports for these four geometries were started. The final comparison
will use the selected five routes and qualified activity reports.

The extracted 14,900 ps reports now pass the shared arrival and
CPPR checks for all four completed routes. SECDED halt has +130 ps
setup and +26 ps hold slack. The five-arm operating period still
depends on the refill implementation.

The native Innovus export produced twelve verified PNG files for
these four checkpoints. The final export can reuse a capture only
when its checkpoint, routed netlist, producer record, capture Tcl,
detail dimensions and image digests match the selected route.

SECDED refill synthesis passed with 9,769 mapped flip-flops,
equal to the RTL-declared total. The count includes 121 check
bits, one sticky failure bit and 11 refill control bits. Genus
reported 165,821.778 µm² of mapped cell area. The full matched
route gate now has all five synthesis producers. Routed area for
refill continues to depend on its geometry checks.

The implemented-clock gem5 runner is queued behind the primary
follow-ups to preserve the 16-process limit. It requires the
actual selected checkpoints and common extracted clock to pass the
provenance checks before launching. It uses the frozen six-workload
grid, retains the source arrival law in absolute time, and reruns
the clean gate when the implemented period differs.

## All five common-die geometries qualify

The routed SECDED refill block occupies 233,604.468 µm² at
73.577% die utilization. The common-die gate selected all five
routes with clean DRC and signal and power/ground connectivity.
Lease4096's selected placed area is 4.65% lower than SECDED
refill's, under the same 317,498.436 µm² die contract.

At 14,900 ps, SECDED refill has −383 ps setup and +1 ps hold
slack. The failing setup path starts at a returned row tag input
and ends at a raw-history SECDED check register. The other four
arms passed at this period. The next shared-clock recheck is
16,000 ps. No refill period or power is inferred from halt-only
SECDED results.

## Qualified common operating clock and selected layout bundle

All five selected GPDK45 history blocks passed the extracted STA
gate at 16,000 ps (62.5 MHz). Rechecked row and taken-target
arrival bounds were 6,641 ps and 9,582 ps. The common contract
keeps the two-cycle query and two-cycle lease service. Thus the
nominal lease service is 32 ns at this clock, after its ownership
drain. The drain remains workload- and state-dependent.

| Protection | Setup slack (ps) | Hold slack (ps) |
| --- | ---: | ---: |
| Unprotected TAGE | +1,720 | +19 |
| Lease4096 | +2,209 | +19 |
| SECDED halt | +1,230 | +26 |
| TMR | +2,019 | +2 |
| SECDED refill | +467 | +1 |

The selected common-clock ledger passed provenance validation.
Its five routed netlist hashes matched the standalone raw
Innovus exports. The local layout ZIP verified 15 images and
three evidence files. Clean gated activity and power extraction
have started at 62.5 MHz.

## Matched post-route power and energy

Xcelium RTL and routed output sequences matched for each measurement.
The power reports show 100% annotation of flip-flop outputs and nets.
The clean measurements use the same 62.5 MHz input trace and the slow
0.9 V view. Energy integrates the reported average power over the
common measurement window of approximately 1.28 ms.

| Protection | Placed cell area (µm²) | Clean total power (mW) | Clean window energy (µJ) |
| --- | ---: | ---: | ---: |
| Unprotected TAGE | 219,765.438 | 1.821245 | 2.331237 |
| Lease4096 | 222,730.920 | 1.866221 | 2.388808 |
| SECDED halt | 227,828.088 | 1.701208 | 2.177587 |
| TMR | 228,084.246 | 1.784180 | 2.283793 |
| SECDED refill | 233,604.468 | 1.739324 | 2.226376 |

Lease4096 uses 1.35% more placed cell area than unprotected TAGE and
2.24%, 2.35%, and 4.65% less than SECDED halt, TMR, and SECDED refill,
respectively. At the common clock, Lease4096 has 979 ps more setup
slack than SECDED halt and 1,742 ps more than SECDED refill. In the
clean trace it draws 9.70% more total power than SECDED halt and 7.30%
more than SECDED refill. Lease4096 has both higher internal power and
higher net switching power than either SECDED block in this trace.

The fixed-length K0, K1, and K2 fault scenarios record energy and
accepted responses separately. In K2, Lease4096 consumes 0.311056 µJ
with 649 accepted responses, SECDED halt consumes 0.097119 µJ with
zero accepted responses and 5,201 stopped edges, and SECDED refill
consumes 0.278111 µJ with 633 accepted responses. These energies apply
to equal elapsed windows whose completed work differs. They do not
estimate workload completion energy.

The local `TAGE_FourWay_GPDK45_PPA_r2.zip` evidence bundle includes
20 raw power reports, the selected route and STA reports, the activity
tables, and the figure source. Both PNGs reproduced byte for byte from
a fresh extraction. The CPU confirmation cohort continues independently.

## Storage and completion figure validation

The storage figure separates the 346 active payload bits and their
check or replica bits from the incremental protection control and
the full RTL declaration. It counts the raw ring once. Lease4096
adds 15 control bits. SECDED halt adds 121 check bits and one
control bit, and refill adds another 11 control bits. TMR adds
692 replica bits. The exported storage CSV also reports synthesized
flip-flops and the smaller native fault target catalog separately.

The area-versus-completion exporter requires the implemented CPU
producer to cite the exact clock and selected-route evidence from
the PPA manifest. It checks the frozen grid digest and every
implemented run and pair identity, timing, and method configuration.
The plot uses verified completions and displays the observed seed
range. The companion CSV retains the correct, valid, and scheduled
denominators and leaves missing conditional times blank. A synthetic
fixture exercised 60 cells and verified seven blank times with zero
correct completions. Input labeled with the pilot's matched timing
failed the join. The synthetic timing fixture is excluded from
measurement evidence. The measured area-versus-completion figure
awaits the complete implemented-clock CPU ledger.

## Complete pilot evidence archive

An independent terminal audit reopened all 195 pilot runs. It
reconstructed direction counts and completion from the final gem5
stats and native counters, verified the resolved configuration
and golden output hashes, and regenerated all 36 paired SOURCE
tapes and their TMR replica mappings. It verified the applied
XOR prefix and censored tail for every run. There were 165 correct
completions and 30 detected SECDED halt stops.

The private `TAGE_FourWay_Complete_Pilot_Evidence.zip` archive
contains 1,741 verified items, including the raw statistics,
configuration, terminal records, applied traces, tape bytes and
hashes, planned grid, figures, and reproduction scripts. It
records stdout byte counts and digests from the independent
audit. The benchmark assets and stdout bytes remain on the
experiment server. A fresh extraction reproduced all nine PNGs
and six data CSVs byte for byte. These are the complete
controlled-clock pilot observations. The frozen confirmation
cohort is still running.

## Frozen native fixed-intensity diagnostic

The follow-up uses single-bit events at 2,000/346, or 5.780,
flips per cataloged bit-second. This makes the ordinary native
catalog's expected rate exactly 2,000 events/s. Lease4096,
SECDED halt, TMR, and SECDED refill have expected rates of
2,075.145, 2,699.422, 6,000, and 2,699.422 events/s, respectively.
The rates differ because the exposed inventories differ.
Every shared semantic site receives the same absolute-time event
in each arm that contains it. The law uses individual bit events
and assumes no physical adjacency.

The frozen design contains Quicksort, SHA-1, and CRC32, four seeds
per workload disjoint from the pilot and both confirmation grids,
and five arms per seed. It references 15 original verified clean
runs at 13,850 ps and schedules 60 fresh faulted runs. Each cell
retains the paired union tape and the exact filtered tape for each
arm. The preparation gate verified the admitted binary, input
and output hashes, the source clean configurations, the native
target counts, and all 12 pair manifests. The five earlier
directed bit-delivery audits were reproduced. The diagnostic
queue waits behind the existing CPU producers so the aggregate
gem5 concurrency stays within 16. The design and tapes are under
`fourway-fixed-per-bit-20261119-r1` on the experiment volume.

The workload diagnostic covers the enumerated active history,
check/replica state, and lease age counter. The full declared RTL
storage exposure remains the earlier separate block-level replay.
The broader control, ring, checkpoint, and query state has no
workload-level measurement under this diagnostic.

## Absolute paired pilot differences against SECDED and TMR

The absolute comparison export checks the full 195-run ledger
against the pilot plan and keeps all scheduled pairs. Its 48 cells
match the earlier paired analyzer's available-pair denominators
and direction metrics. It reports Lease4096 minus the comparator
in milliseconds, equal-clock cycles, MPKI, and accuracy percentage
points. Performance means use pairs in which both methods exited
correctly with verified output. The four pilot seeds per nonzero
cell are below the paired interval reporting minimum.

Both SECDED refill and TMR completed all 36 faulted runs per arm.
At 2,000 events/s, all four seeds per workload are comparable
against these arms. The differences below are means of the paired
effects for the 13,850 ps controlled clock.

| Workload | Lease minus refill (ms) | Lease minus refill (MPKI) | Lease minus TMR (ms) | Lease minus TMR (MPKI) |
| --- | ---: | ---: | ---: | ---: |
| Quicksort | +1.854 | +0.3870 | +2.024 | +0.4076 |
| SHA-1 | +0.366 | +0.2034 | +0.377 | +0.2064 |
| CRC32 | +3.944 | +0.000029 | +5.147 | +0.000029 |

Lease4096 finished 0.019 ms earlier than both refill and TMR on
SHA-1 at 20 events/s while recording slightly higher MPKI. The
clean SHA-1 run was already 0.022 ms earlier with the same
direction counts, so the low-rate time advantage provides no
evidence of superior direction resilience. On CRC32 at 8,000
events/s, the time gap against refill narrows to +0.245 ms, while
the gap against TMR remains +5.178 ms. No matched time is available
against SECDED halt at either 2,000 or 8,000 events/s. All 12
halt runs across the three workloads stopped at each of those rates.
The completion table keeps those outcomes and the paired time
table leaves the corresponding cells blank.

## Data-only handoff

The updated deliverable is verified experiment data and reproduction
material. Presentation and figure production has been removed from
the queued export. The exporter validates the complete terminal
cohort against the frozen plan, audits raw stats, terminal records,
output digests and tape delivery, then writes numerical tables. For
the hardware-feasible cohort it also validates the exact routed
clock and configuration match before writing the area and
completion CSV.

The pilot exercised the data-only pipeline on all 195 terminal
runs. The preliminary `TAGE_FourWay_Raw_Data_Pilot_and_PPA.zip`
archive includes 1,795 verified files covering the pilot, the
recomputed legacy baseline, the matched GPDK45 physical data,
source, and validation records. A new extraction reproduced the
four pilot CSV tables byte for byte. The archive excludes charts
and presentation files. The ongoing confirmation and diagnostic
campaigns will produce separate raw ledgers.
