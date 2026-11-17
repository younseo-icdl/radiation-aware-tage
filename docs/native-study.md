# Native fault and recovery observations

The 2026-11-16 development/evaluation producers are frozen historical outputs.
The integrated continuation adds optional policies and observations in fresh
producers; it does not backfill their missing observables or extend that owner
sample. Use matching committed Python configs when reproducing an older binary
whose SimObject parameter interface predates these additions.

`simulation/gem5/configs/native_study.py` uses ordinary upstream TAGE through a
thin subclass. It calls upstream prediction, training, RNG, history update, and
squash operations without an additional finite controller, checker stage,
periodic service clock, lookup hold, retirement hold, or post-exit advance.
`baseline.create_system` provides the same CPU/cache/memory geometry used by the
clean comparison. This is the unprotected fault comparator, not a candidate.

Prepare a fresh producer after committing maintained sources:

```sh
.venv/bin/python tools/gem5.py prepare --tree build/gem5-native-study-r1
.venv/bin/python tools/gem5.py build --tree build/gem5-native-study-r1 --jobs 16 --cxx /opt/rh/gcc-toolset-13/root/usr/bin/g++
.venv/bin/python tools/gem5.py run --tree build/gem5-native-study-r1 --config simulation/gem5/configs/native_study.py --outdir work/native-check-clean -- --binary build/checksum --diagnostics --execute
```

Use the actual checksum executable path from the local build. Output directories
must be fresh. `--schedule FILE` accepts an explicit `# time_unit=ticks` header
and rows `TICK SITE[;SITE...]`. R0 is the youngest active raw bit; Wn:b selects a
history word/bit. Integer sites address the logical manifest. Each row is one
atomic XOR group; duplicate sites are rejected, and separate equal-tick rows are
separate events. Physical hardware placement and whole-state coverage are not
claimed. Injection precedes the CPU tick at the same simulated timestamp.

`--diagnostics` records gzip committed-branch observations, lookup-time source
snapshots, and sparse raw-origin observations. Retirement time is obtained from
the O3 commit hook; training time is recorded separately. The source snapshot is
after the TAGE query and before speculative append. Missing joins are explicit
and counted; they must be zero before recovery analysis. Origin labels follow
actual raw-buffer append, undo, and rollover, including observed restorable
heads. Labels denote provenance, not necessarily a current semantic error.
Multi-event recovery partitioning and path-origin tracking are not implemented.

Different speculative histories do not automatically align faulted and clean
snapshots. Such state comparisons require an explicit alignment test or remain
N/A. A first zero is not stable recovery; retain recurrence and right censoring.
Program completion freezes fault scheduling and closes the gzip stream without
advancing model time. Pending ordinary branch-history observations are reported,
not represented as a finite-helper drain failure.

Before workload use, check clean diagnostic transparency, explicit XORs and
future-event censoring on the bounded checksum, valid trace termination and
joins, and the existing finite checksum regression. These are tests of new code,
not a new historical authenticity campaign. No MF speedup can be claimed from
UF data alone; protection costs must be charged in a later matched comparison.

The reusable bounded test is `tests/gem5/native.py --tree TREE --output FRESH`
(run with the project Python). Optionally pass `--native-reference` pointing to
the ordinary-native checksum cell from the finite gate. The first local attempt
found an incorrect interrupt responder connection in the shared CPU factory;
that attempt is retained, the connection was corrected to the memory-side port,
and all subsequent native and finite checks passed.

Analyze one matched CPU pair with:

```sh
.venv/bin/python -m simulation.analysis.native --clean U0_DIR --fault UF_DIR --output FRESH_ANALYSIS
```

The reader streams complete gzip traces, rejects architectural branch-sequence
divergence, checks retirement identities and output, and uses actual retirement
ticks at every conditional branch. The fixed rule is three consecutive full
1024-conditional windows with zero incremental excess time and no finer
positive/negative cancellation or prediction differences. A constant retained
cumulative time gap is allowed. Reference-fold comparison is available only at
equal raw/path/nonspec source snapshots; missing alignment remains explicit.
Full learning-state recovery is not exported by this CPU trace.
Prediction differences and harmful/helpful labels refer to TAGE's conditional
direction, before final BPU target/BTB overrides. They are not automatically CPU
redirects. Exact retirement time remains measured independently. The timing
rule conservatively excludes TAGE-direction differences and does not certify
the unobserved final BPU direction/target milestone.

## One admitted direct-query candidate

The initial native screen found a 15.72% qsort runtime penalty at the declared
R0 owner, versus approximately 0.155% at R64. This motivates one candidate rather
than a broad design/rate sweep: `--direct --query-latency 1`. Direct queries use
the current raw history and original path/hash functions, with no oracle copy,
table clearing, or stored-fold repair. Raw writes, training order, allocation,
and speculation retain upstream behavior. Dead rolling-fold software fields are
retained only for upstream bookkeeping; they do not supply direct query hashes
or represent required direct hardware storage. Stored-fold injections are N/A
for this candidate. The common comparison environment is raw-history-only.

An additional one-cycle conditional-query wait is charged before the actual
query, with one pending request, explicit token ownership and squash cancellation.
No data is computed from a future source snapshot: source is read when the query
is consumed. The admission interface can start the next request after consumption;
its single outstanding request is explicit rather than a claimed multi-request
pipeline. There is no added raw-update or retirement stage, periodic checker,
protected gold copy, or post-exit service. Physical latency, energy, fanout,
checkpoint/control protection, and area are UNKNOWN. One cycle is a declared
architectural modeling assumption, not a measured 45 nm timing result.

Admit three qsort cells: M0 and MF at each of the already declared R0/R64 ticks.
Use the existing same-geometry U0/UF cells after focused native-path regression;
do not repeat them solely for a producer label. Zero-latency direct is a bounded
implementation-equivalence control only. Report M0/U0 cost and MF/UF benefit
separately, including a loss at either owner. No independent evaluation or
environment-wide SEU benefit is implied by these development owners.

## Integrated development interface

New producers add `--direct-bank-mask` for static whole-bank hybrids, and
`--lease-period K --lease-service-cycles L` for a separate quiescent rebase
hypothesis. The latter counts actual speculative raw appends, including
unconditional-branch history updates. It stops new admissions, waits for both
the actual BPU deque and every live TAGE history owner to drain, then charges
service and publishes Phi of its current own raw source. It neither repairs
raw state nor copies reference learning. Lease/direct/delayed-query combinations
are not admitted. Period zero and mask zero retain the ordinary native path.
The initial service latency is a declared development assumption; neither B0
mapping nor a C++ gate qualifies its physical source/read/undo/worker interface.
Once started, publication is an autonomous completion event, even while fetch
waits for memory. It is not deferred until a convenient later observer call.
Same-tick digital order is injection, lease publication, then CPU tick. The
lease event log records exact start/deadline/publication and empty-owner gates;
pending completion at program exit is censored without advancing simulation.

`--cycle-ticks` sets the CPU period in the default 1 ps gem5 timebase. It does
not rescale absolute-tick fault tapes or their fixed events/second law. Header
`horizon=` is reported as declared tape coverage, with exhaustion before exit
explicitly flagged. Injection logs now include bit values before/after each
atomic group. `L:AGE:b` exposes the lease age bits for directed control tests;
busy/timer coverage remains incomplete, so the manifest does not claim WHOLE.
Unused hybrid folds are marked unconsumed and cannot be injected as live state.

Read-only BPU hooks capture final predicted direction/target, BTB status and
actual committed misprediction status, separate from TAGE's conditional result.
The regression reconciles those flags with committed BPU statistics. Old traces
lacking these fields remain explicitly limited. Peak actual BPU and all-live
history ownership, same-tick queries, raw appends and restores are recorded to
size the physical interface rather than assuming one query/undo per cycle.
The finite owner capacity is declared and asserted, not inferred to cover all
possible workloads from a small sample. Exact training/RNG operations continue
through the unchanged upstream `TAGE::update`.
