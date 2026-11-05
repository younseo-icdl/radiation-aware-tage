# Build and run

## Local dependencies

Use Python 3.10+ and a C++17 compiler. gem5 v25.1.0.1 supports GCC 11 through 14.2. On the current server use GCC 11 from `/opt/rh/gcc-toolset-11/root/usr/bin/`.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make -j4 test all PYTHON=.venv/bin/python CXX=/path/to/g++
make checksum CC=/path/to/gcc
```

If the system Python is old, create the venv with an available newer interpreter. On the current server `/opt/miniconda3/bin/python` is available. No sudo or global package installation is needed.

`build/tage-sim` uses standalone gem5 interface shims and the shared backend. It is not an instruction-set or cycle simulator. `make clean` removes only its generated object, replay executable, and C++ test binaries; it does not delete a gem5 tree or experiment outputs.

## Prepare gem5

```bash
.venv/bin/python tools/gem5.py prepare --tree build/gem5
.venv/bin/python tools/gem5.py build --tree build/gem5 --jobs 8 --cxx /path/to/g++
```

Preparation clones the official pinned upstream tag, verifies its commit, then copies the canonical TAGE modules and the O3 overlay into the new tree. It refuses an existing destination. For a changed producer, prepare a new tree rather than copying over a running producer. `--cxx` selects that compiler and its sibling `gcc` for the build process only. The helper also selects the active Python's config and library directory without changing shell startup files.

The finite SimObjects are registered in gem5's predictor SConscript. The backend under `tage/backend/` is the single maintained backend. Full upstream source, generated bindings, and compiled binaries remain under the ignored build directory.

## CPU smoke and fault schedules

After building gem5, run the reusable 14-case O3 regression (nine clean configurations and five fixed-injection checks):

```bash
make gem5-test PYTHON=.venv/bin/python GEM5_JOBS=8 GEM5_OUTPUT=work/checksum-gate
```

This checks all four baselines, periodic parity, exact direct, L=2, the early checkpoint variant, source upsets, and head/FIFO/order metadata repair. Every run must match the native checksum and complete finite helper drain. It refuses an existing output directory and terminates a timed-out simulator process group. These are correctness probes, not a scientific performance campaign.

```bash
make checksum
mkdir -p work
build/checksum > work/native.stdout
.venv/bin/python tools/gem5.py run --outdir work/checksum-native -- \
  --binary build/checksum --model native --execute
.venv/bin/python tools/gem5.py run --outdir work/checksum-ecc -- \
  --binary build/checksum --scheme P_ECC --execute
cmp work/native.stdout work/checksum-native/program.stdout
cmp work/native.stdout work/checksum-ecc/program.stdout
```

The checksum is a freestanding Linux x86-64 program. It prints `checksum: 2bf45f80b1c37877`. It is a regression workload, not SPEC or a representative performance benchmark.

Use `--representation recurrent|direct`, `--query-latency 1|2`, `--update-latency 1|2`, and one of the four schemes. Periodic parity uses `--scheme P_ED --inspection-interval 64`. Direct folding is an additional P0 representation with source update L=1; the configuration rejects an apparent direct update L=2. `--early-unconditional` selects the separate early checkpoint path. The clean `--model native` reference uses the instrumented backend's ordinary timing path; it is not a separate pristine upstream build.

Generate a cycle-based SOURCE schedule:

```bash
.venv/bin/python -m radiation --seed 548 --horizon 1000000 --rate 1e-6 \
  --scope raw --multiplicity charm --time-unit cycles --output work/source/events.txt
.venv/bin/python tools/gem5.py run --outdir work/checksum-fault -- \
  --binary build/checksum --scheme P_ECC \
  --schedule work/source/events.txt --execute
```

A short workload may terminate before a generated event; check `applied_events` and `future_events_censored` before interpreting it as an injection test. For deterministic stage gates use an explicitly fixed tick/site event.

A schedule row is `tick R<age>` or `tick W<word>:<bit>`, or an absolute logical site ID from that producer's manifest. Separate simultaneous flipped sites by semicolons. `R` and `W` aliases resolve at injection time. Absolute IDs are producer-specific. Clock events, detector checks, and fault events have explicit event priority in the implementation.

At successful finite termination, inspect `seu.program_exit.json`, `seu.json`, `termination.json`, `events.csv`, `program.stdout`, `program.stderr`, and `stats.txt`. `termination.json` verifies actual helper completion without extending exposure or workload statistics. `logical_manifest.json` declares modeled storage, assumptions, and exclusions.

`--initialize-only` performs tick-zero construction and state-map generation. It does not run CPU instructions and is not a program correctness PASS.
