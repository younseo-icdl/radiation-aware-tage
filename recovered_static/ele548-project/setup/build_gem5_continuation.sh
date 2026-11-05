#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
export LD_LIBRARY_PATH="/opt/miniconda3/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
.venv/bin/python scripts/prepare_gem5_continuation.py
if [[ ! -d third_party/gem5-continuation/build/X86_STAGE0 ]];then
 mkdir -p third_party/gem5-continuation/build
 cp -a --reflink=auto third_party/gem5-periodic/build/X86_STAGE0 third_party/gem5-continuation/build/
fi
cd third_party/gem5-continuation
/usr/bin/time -f '%U %S %M' -o ../../continuation/runtime/reports/G4_BUILD.time ../../.venv/bin/scons build/X86_STAGE0/gem5.opt -j2
