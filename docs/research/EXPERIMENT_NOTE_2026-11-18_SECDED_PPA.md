# Matched history-block SECDED and lease4096 PPA

## Implemented boundary

The staged history block retains its history ring, head, path
checkpoint array, undo and append interfaces, registered query, and
returned-row selection. The SECDED arm protects the established
S* payload of 346 logical bits: the active raw130 word, 21 folded
words totalling 200 bits, and current path16. It adds 121 stored
check bits and a sticky uncorrectable-error latch. Head, older
retained raw ages outside the current 130-bit window, checkpoint
rows, and external predictor arrays remain outside this code
coverage. They are still present wherever they belong to the
measured history boundary.

The decoders feed corrected data directly into the query and
history RMW paths. A clean history operation re-encodes its final
raw, fold, and path values. On an idle edge a correction can
write back the affected raw bit or carry corrected fold, path,
and check bits back to storage. A corrected raw payload bit is
forwarded into a simultaneously restored view when that view
still contains the bit. An append to the same physical ring
row takes priority over repair of the old value. A detected
uncorrectable word disables admission and state mutation until
reset. This is the measured RTL containment behavior. A CPU
fallback/refill implementation is outside this physical block.

## First gates and measurement conditions

Xcelium passed the directed raw/fold/path and check-bit read and
writeback controls, including undo, an append collision, and a
same-word double error. Clean stimulus replay passed 80,001
edges and 14,519 returned-row predictions per arm. Both arms used
the same lease-generated input vectors. The four lease maintenance
windows are electrically idle input cycles in the ECC arm. There
is no injected fault in this common activity window. Faulted
writeback is verified in the directed gate.

Fresh Genus and Innovus producers use the same GPDK45 libraries,
clock and I/O constraints, and initial 543.349 µm core width and
height. The first timing test uses a common 13.850 ns period,
including the existing 6.641 ns row and 9.582 ns target-valid
late arrivals. Require 65–75% die utilization, DRC and both
connectivity checks before accepting a routed case. Extracted
setup, hold, query, and returned-row timing determine whether
the initial period is feasible. Compare activity-based power
only at a common qualified period and on identical input edges.
Track zero-delay gate activity and annotation coverage separately
from extracted timing. Raw logs and independent producers are
under `work/history-secded-ppa-20261118-r1/`.

The standalone C++ suite and 70 Python checks passed. The
existing checksum-qualified gem5 executable also passed all 14
finite checksum cases. Its P_ECC case validates the software
model. The Xcelium test and trace replay establish the separate
RTL and do not change the gem5 integration.

## First lease route and synthesis retry

The first fresh lease map and route completed. The placed cell
area was 226,523.700 µm² at 71.346% die utilization. A separate
extracted timing audit is running. The first ECC Genus process
was still active after one hour. Its log had reached technology
mapping and started worker processes, but the main process was
using most of the observed CPU time. The original run remains
live with its longer synthesis limit.

A second independent pair disables automatic hierarchy ungrouping
for both SECDED and lease. It tests a mapping alternative with
the same logic, clock and libraries in separate producer
directories. Neither arm mixes a mapped result from the other
strategy for its primary pair. The independent logs and
checkpoints are under `work/history-secded-ppa-20261118-r2/`.

The first lease route's extracted CPPR audit marked setup at
-496 ps with the common 6.641 ns row arrival. The worst early
path was a row-request PC output assertion reported as a
negative slack rounded to 0 ps. Both are retained as timing
failures at 13.850 ns for that fresh placement. The previously
published lease placement remains a distinct producer.

The user increased the allocation to 16 cores for each arm.
Cadence synthesis reads its worker configuration at launch.
The 4-core hierarchy-preserving retry was stopped, retaining
its partial logs. A fresh hierarchy-preserving ECC/lease pair
uses 16 cores per Genus, Innovus and Voltus producer under
`work/history-secded-ppa-20261118-r3/`. The original ECC
mapping is retained as an independent fallback.

## 16-core pair through mapping

Both hierarchy-preserving maps completed. Genus mapped 64,609
cells and 165,745.512 µm² for SECDED and 61,660 cells and
161,671.266 µm² for lease4096. SECDED mapped cell area was
2.52% larger at this stage. Worst Genus data paths were 12.125 ns
and 8.134 ns respectively under the synthesis I/O assumptions.
These are wireload paths; they do not substitute for the
extracted late-operand timing under the shared constraints.

The 16-core lease route completed at 223,445.016 µm² and
70.377% die utilization, with DRC and both connectivity
checks passing. The extracted common-period recheck with
late row and target arrivals passed at 13.850 ns with
+426 ps setup and +16 ps hold slack. SECDED is routing with
the same settings. The original automatic-ungrouping ECC
producer was independently active.

## Extracted closure and gate-level reset check

The matched 16-core SECDED route completed with 233,071.290 µm²
of placed cells at 73.409% die utilization. Both arms used the
same die and passed internal DRC and signal and supply connectivity.

The CPPR recheck at 13.850 ns gave SECDED -988 ps setup and +5 ps
hold. The limiting setup path launches at a returned row-tag
input and terminates at a raw SECDED check-bit register. Lease
met the same constraints with +426 ps setup and +16 ps hold.
At 14.900 ns, SECDED closed with +65 ps setup and +5 ps hold,
while lease closed with +1,085 ps setup and +16 ps hold.
The common-period power comparison uses this verified 14.900 ns.

The first routed SECDED activity replay stopped before edge zero
because the reset sequence left X in portions of the raw ring.
Waveform tracing found unknown feedback at the data pin of a
representative raw flop during synchronous reset; the raw decoder
then propagated it to admission. RTL reset had passed. Lease
passed the first routed replay. An independent paired retry
specifies identical concrete all-one simulation initialization
before the existing synchronous reset. Its outputs will be
admitted only if reset and the same clean trace pass. The original
failed wave and log remain available.

## Final matched routed comparison

The successful Xcelium setup used `-xminitialize 1
-delay_udp_xminitialize` so the library's UDP-based D flops
started with concrete states before the normal reset. The
earlier `-initreg1` setting did not initialize those UDPs.
The ECC directed reset replay passed for both initial zero and
initial one. The all-one VCD showed all 1,024 raw storage
outputs high before the first reset edge and low after it.
The common power window starts after the four reset edges.
Both complete routed replays then passed all 80,001 edges,
14,519 responses, and the single cancellation. The lease arm
published four times. The full gate waveforms and reports are
under `work/history-secded-ppa-20261118-r3/activity-reset-qualified-{ecc,lease4096}/`.

The final pair used the same 317,498.436 µm² die, 14.900 ns
common clock, and identical clean input trace at the slow
0.9 V power view. Every flop output and net was annotated
in both arms. ECC had 9,758/9,758 annotated flop outputs and
93,330/93,330 annotated nets. Lease had 9,652/9,652 annotated
flop outputs and 90,833/90,833 annotated nets.

| Routed metric | Lease4096 | SECDED |
|---|---:|---:|
| Placed cell area (µm²) | 223,445.016 | 233,071.290 |
| Die utilization | 70.377% | 73.409% |
| Setup slack at 13.850 ns (ps) | +426 | -988 |
| Setup slack at 14.900 ns (ps) | +1,085 | +65 |
| Hold slack at 14.900 ns (ps) | +16 | +5 |
| Internal power (mW) | 1.370236 | 1.348331 |
| Switching power (mW) | 0.623886 | 0.475565 |
| Leakage power (mW) | 0.005293 | 0.005508 |
| Total power (mW) | 1.999415 | 1.829405 |
| Common-window energy (µJ) | 2.383347 | 2.180691 |

ECC cost 4.31% more placed cell area. Its raw check-bit write
path missed the prior shared clock, while 14.900 ns closed
both checkpoints. This establishes the verified shared period
for the power experiment, with no minimum-period sweep. On
this clean trace, ECC used 8.50% less power and window energy.
The largest measured component difference was lower estimated
switching power. The matched gate results show that component
gate counts alone do not predict routed activity power.

The signal activity trace uses zero cell delay with extracted
RC for power. It covers the integrated clean history path,
including active ECC read/check and re-encoding. The directed
RTL gate exercises faulted repair writeback. The clean power
window does not measure the energy of an injected repair
episode or of external CPU recovery. Both arm energies refer
to the same input edges including lease-generated idle gaps,
not maximum throughput or whole-CPU energy. The original
automatic-ungrouping ECC map hit its three-hour host limit.
The qualified 16-core hierarchical pair provides the reported
matched comparison. No TMR PPA producer was run.

Machine-readable closure and power figures are
`TIMING_13850.json`, `TIMING_CLOSED.json`, and
`PPA_RESULT.json` in the final producer directory.
