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
