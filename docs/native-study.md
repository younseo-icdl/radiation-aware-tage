# Native fault and recovery observations

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
