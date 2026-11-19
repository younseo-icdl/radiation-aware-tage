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
The initial gate also checked post-exit censoring. Add explicit
rollback and refill-boundary probes before admitting the pilot. Native refill still needs an old-epoch
drain, committed-only refill progress, base predictor training,
and a post-refill owner drain before tagged lookup resumes.
Do not count speculative appends as committed refill progress.

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
