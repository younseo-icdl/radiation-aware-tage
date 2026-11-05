#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/rh/gcc-toolset-11/enable
export LD_LIBRARY_PATH="/opt/miniconda3/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
"$ROOT/.venv/bin/python" "$ROOT/scripts/prepare_gem5_e3.py"
cd "$ROOT/third_party/gem5-e3"
"$ROOT/.venv/bin/scons" build/X86_STAGE0/gem5.opt -j8
./build/X86_STAGE0/gem5.opt --build-info
