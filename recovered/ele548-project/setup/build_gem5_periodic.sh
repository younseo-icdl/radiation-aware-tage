#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
export LD_LIBRARY_PATH="/opt/miniconda3/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
.venv/bin/python scripts/prepare_gem5_periodic.py
if [[ ! -d third_party/gem5-periodic/build/X86_STAGE0 ]]; then
    mkdir -p third_party/gem5-periodic/build
    # Reflink where available; otherwise ordinary independent copies.
    # Never hardlink mutable build artifacts to the completed producer.
    cp -a --reflink=auto third_party/gem5-e3/build/X86_STAGE0 third_party/gem5-periodic/build/
fi
cd third_party/gem5-periodic
../../.venv/bin/scons build/X86_STAGE0/gem5.opt -j8
./build/X86_STAGE0/gem5.opt --build-info
