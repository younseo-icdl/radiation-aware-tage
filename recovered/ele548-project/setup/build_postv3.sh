#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
export LD_LIBRARY_PATH="/opt/miniconda3/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
.venv/bin/python scripts/postv3_prepare.py
cd third_party/gem5-postv3
attempt=${1:-1}
/usr/bin/time -f '%U %S %M' -o "../../postv3/runtime/reports/BUILD_${attempt}.time" ../../.venv/bin/scons build/X86_STAGE0/gem5.opt -j2
