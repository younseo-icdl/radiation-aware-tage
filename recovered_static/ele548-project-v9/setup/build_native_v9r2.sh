#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
export LD_LIBRARY_PATH="/opt/miniconda3/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
.venv/bin/python setup/native_v9r2_prepare.py
task_out="$(pwd)/rate_state_v9/r2/runtime"
test ! -e "$task_out/reports/BUILD_1.time"
cd third_party/gem5-native-v9r2
/usr/bin/time -f '%U %S %M' -o "$task_out/reports/BUILD_1.time" ../../.venv/bin/scons build/X86_PIPELINE/gem5.opt -j2
