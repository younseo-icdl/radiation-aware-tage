# Production-kernel propagation experiment

Question: how can a stored raw bit not currently read by a fold change that fold
later? Alternative: coherent wrong incoming history cancels at window exit,
whereas stored raw-only corruption leaves a residual because its outgoing XOR
no longer matches the value incorporated earlier.

`simulation/cpp/fold_causality.cpp` calls the actual pinned
`TAGEBase::FoldedHistory::update`, exposed through a derived test class. It does
not copy that implementation into an explanatory simulator. A separate direct
XOR oracle computes Phi(H). The experiment represents the post-append production
call phase, using new h[0] and h[L]. This is a forward-only kernel experiment;
it does not execute full `updateHistories`, learning, CPU timing or speculation.
Existing setter/deep-copy/rollback tests and CPU gates remain separate evidence.

## Predeclared conditions and execution

Seven real bank lengths, each real index/tag0/tag1 width, all 130 injection ages,
four deterministic input patterns (zero/one/alternating/mix64), and 260 updates
after injection. The seven arms are clean, raw-only stored upset, coherent wrong
incoming, fold-only upset, raw repaired before tap, raw repaired after tap, and
immediate canonical rebuilding from current own raw. All arms use the same
subsequent input. Coherent history is created by an actual wrong incoming update
during warmup, not by changing both raw and folds at observation time.

The gold raw-repair arms are diagnostics only. The rebuild arm uses its own
possibly wrong raw; it receives no reference bit or injection location. These
are deterministic contrasts, not seven independent particle events.

```sh
make build/tage-fold-causality CXX=/opt/rh/gcc-toolset-13/root/usr/bin/g++
build/tage-fold-causality work/FRESH_OUTPUT
```

Actual first output: `work/professor-causality-20261117-r1/`, with `RUN.json`
source/binary identity, `SUMMARY.csv` and `HAND_TRACE.csv`. Output overwrite is
rejected. PASS: 10,920 parameter cases and 19,950,840 arm observations. These
observations are not independent statistical samples or CPU runs. No failure or
new expensive CPU experiment was required.

## Results

- Clean and coherent-input folds equal independent Phi(H) at every observation.
- For a<L, stored raw-only corruption first changes reference fold at exactly
  L-a updates. For a>=L, that bank has no forward stored-fold effect. No-effect
  cells use -1/not observed in CSV, never a measured zero-delay effect.
- Raw-only has d_ref=0 immediately while d_inv can already be one. Once the
  outgoing tap consumes it, its nonzero reference residual rotates with constant
  Hamming weight. All remaining input/taps match, yet it persists through260.
- Coherent wrong incoming has a temporary reference-fold difference, disappearing
  at window exit. Fold-only upset instead leaves a one-bit rotating residual.
- Restoring raw before tap prevents the residual. Restoring raw after tap does
  not repair it. Rebuilding immediately from own raw makes d_inv zero but still
  differs from the reference until that coherent wrong history expires.

Hand trace: actual bank3 tag0 has L=15, width10. Zero input, age3 raw-only event
after completed update. The first changed outgoing consumption is update12;
the stored fold remains zero through11, then becomes32 at12 and64 at13.
Coherent wrong incoming instead has fold8 at0, then returns to zero at12.
This bank's raw window is clear at12, but the shared raw130 copy persists until
update127; source lifetime and per-bank window exit are different coordinates.
The trace logs incoming/next-outgoing, stored/reference/Phi, both distances and
both raw-difference scopes. No head/epoch/owner is fabricated in this kernel
boundary; those belong to the existing full predictor/CPU diagnostics.

Plots `CAUSAL_PROPAGATION.{png,pdf}` use only these measured CSVs: first difference
versus age with theoretical L-a overlay, and the representative arm timeline.
The top panel shows zero-pattern index folds; all four patterns and three kinds
passed the assertions. Plotting software was installed only in `.venv`.

## Interpretation and next decision

The outgoing-only explanation and delayed fold contamination are consistent.
Do not claim immediate all-bank fold mutation, Hamming-weight amplification,
whole-predictor recovery after130 updates, or CPU slowdown from this unit test.
The archived H/F/table restoration records and 12 current causal replay cases
already address intervention effects. Reuse them with their original horizons;
do not repeat them just for this handoff. Path/table-only and live-copy/undo
routes are separate existing evidence or explicitly scoped missing contrasts.

Proceed with the low-overhead maintenance specification and actual source/undo
cost qualification. A nonblocking snapshot worker still needs epoch/forwarding
or retry and bounded defer; the implemented quiescent worker is an honest,
charged baseline for that question, not a claim that background repair is free.
