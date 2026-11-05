# Radiation-aware TAGE

Research software for studying which TAGE predictor state to protect against single-event upsets, and how protection and repair costs affect CPU performance.

The project separates **radiation modeling**, **predictor implementations**, and **simulation**. A fault schedule is an external experimental input. A protection controller sees only its implemented parity, syndrome, replicas, and protocol state.

```text
radiation/                 Event models, RNG namespaces, public dataset parsers
tage/
  include/tage/
    predictor/             Gshare, plain TAGE, functional protection adapters
    history/               Logical history access and snapshots
    protection/            Parity, SECDED, TMR, exclude/relearn policy
    pipeline/              Finite lookup, source RMW, protection, and control
    transport/             Payload encoding and metadata protection
  backend/cpu/pred/         Shared TAGE backend based on pinned gem5
simulation/
  cpp/                     Functional branch-trace replay and standalone shims
  gem5/                    O3 configurations, core overlay, upstream version pin
  analysis/                Paired-owner A/B/C/D analysis
  workloads/               Small regression workloads
tests/                     C++ correctness gates and Python integration tests
tools/                     Reusable simulator preparation/build commands
docs/                      Architecture, model assumptions, experiment protocol
```

The required baselines are **P0**, **P_ED** (parity with exclude/relearn), **P_ECC** (SECDED), and **P_TMR**, applied to the same selected history state **S*=346 bits**: raw130, path16, and folded200. Periodic parity and exact direct folding are additional finite-model comparisons.

## Quick start

Use Python 3.10 or newer and a C++17 compiler. All installation and generated files stay under this checkout.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
make -j4 test PYTHON=.venv/bin/python
make smoke
```

If the default compiler is too old, pass `CXX=/path/to/g++`. On the current server, GCC 11 is available at `/opt/rh/gcc-toolset-11/root/usr/bin/g++`.

Generate a synthetic branch-exposure schedule and replay it:

```bash
.venv/bin/python -m radiation --seed 548 --horizon 10000 --rate 0.001 \
  --scope raw --multiplicity charm --time-unit branches --output work/example/events.txt
build/tage-sim --demo 10000 --scheme P_ECC --schedule work/example/events.txt
```

This is a **synthetic functional smoke test**. It does not measure CPU slowdown or establish a physical radiation rate.

For external traces, use `--trace FILE`. Each row contains `pc taken target conditional`, separated by spaces or commas; addresses accept `0x` notation. Events use one-based branch ordinals and `R<raw-age>` or `W<word>:<bit>` sites. Multiple sites separated by semicolons form one atomic XOR event.

## CPU simulation

gem5 is pinned to **v25.1.0.1**. Its source and compiled executable are local build products, not vendored binaries.

```bash
.venv/bin/python tools/gem5.py prepare
.venv/bin/python tools/gem5.py build --jobs 8
make checksum
build/gem5/build/X86/gem5.opt --outdir=work/checksum-ecc \
  simulation/gem5/configs/finite.py --binary build/checksum --scheme P_ECC --execute
```

Use a fresh `--outdir` for every run. `--initialize-only` constructs the model at tick zero without executing the workload. See [build instructions](docs/build.md) for compiler selection, native reference runs, fault schedules, and output validation.

## Reading guide

- [Architecture](docs/architecture.md): implementation boundaries and resource model.
- [Radiation models](docs/radiation_models.md): distributions, rates, data semantics, and assumptions.
- [Experiments](docs/experiments.md): selected-state versus whole-state exposure, paired analysis, and correctness requirements.

Keep private benchmark distributions, input traces, papers, raw datasets, and large run outputs outside Git. Shared source and documentation belong in this repository. Documentation and maintained interfaces are in English.
