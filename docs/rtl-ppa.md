# History implementation and physical evidence

History-subsystem RTL/Cadence/PPA was explicitly authorized on 2026-11-17.
The current local reference is GPDK45 with gsclib045_all_v4.8. PDK/library/course
data and generated tool output remain private. No full-CPU RTL or device-level
radiation calibration is in scope.

The first reusable RTL is `tage/rtl/tage_history_hash.sv`. It implements the
original seven-bank hashes with a compile-time direct-bank mask. Mask zero uses
stored folds, 127 uses current raw history in every bank, and mixed masks select
whole banks. The geometry is histories 5/9/15/25/44/76/130, index width 9, and
tag widths 9/9/10/10/11/11/12. Bit zero is the youngest source bit.

`simulation/cpp/rtl_vectors.cpp` uses the pinned C++ TAGE backend for expected
indices/tags; it does not use the RTL algorithm as its reference. Arbitrary
independent raw and stored-fold values cover inconsistent/faulted source states.
`tests/rtl/hash_tb.sv` checks stored, full direct and mixed-bank masks against
those endpoints. Generate private vectors and run from a fresh output directory:

```sh
make build/tage-rtl-vectors CXX=/path/to/compatible/g++
build/tage-rtl-vectors /private/fresh/vectors.txt 20000
csh -c 'xrun -64bit -sv /repo/tage/rtl/tage_history_hash.sv /repo/tests/rtl/hash_tb.sv -top hash_tb +vectors=/private/fresh/vectors.txt'
```

This is **B0 combinational hash** evidence. It contains no raw storage/read
alignment/head, update ports, checkpoint/undo, protection, journal, clock or
maintenance controller. It does not qualify a complete source stage or prove
zero additional CPU latency. B1 must match those actual capabilities and B2
must account for shared predictor tables separately.

Use `python -m simulation.eda.synthesize --site PRIVATE.json --direct-mask MASK
--output FRESH_DIR` for a matched B0 Genus run. The private site selects an actual
Liberty file and common clock/input/output/transition/load constraints. The flow
copies its own RTL/Tcl privately before execution, records source identity and
dirty state, catches Tcl errors, checks exit status and required artifacts, and
retains failed output. It sources the user's csh environment. Public source has
no PDK data or credentials. A generated producer descriptor is not a PPA result.

The existing gsclib045 basic-cell views enumerate slow and fast libraries, not a
TT view. `slow_vdd1v0` actually specifies nominal 0.9 V/125 C and `fast_vdd1v0`
1.1 V/0 C; filenames are not operating conditions. Preserve actual Liberty
units, nominal conditions, tool version, constraints and physical views. Tool
version output, a simulation PASS, synthesis area, placement, routed timing and
activity-based energy are separate gates. Educational cap-table RC and local
DRC do not establish foundry signoff. No 28 nm to 45 nm numerical PPA comparison
is permitted.

`python -m simulation.eda.implement --synthesis PASSED_B0 --site PRIVATE.json
--output FRESH_DIR` runs the corresponding B0 physical flow with matched slow
setup/fast hold views, technology/cell LEF, declared cap-table RC, fixed geometry,
signal routing layers, PG and local checks. It has a virtual clock and no CTS;
it explicitly refuses to qualify full-history timing. A completed flow still
requires inspection of timing, DRV, DRC, connectivity, units and activity before
any implementation claim. Default placement seed is recorded as a limitation,
not invented. This initial helper does not measure activity power.
