#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
export LD_LIBRARY_PATH="/opt/miniconda3/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
.venv/bin/python scripts/v3_prepare_roundb.py
if [[ ! -d third_party/gem5-costaware-v3-b/build/X86_STAGE0 ]];then
 mkdir -p third_party/gem5-costaware-v3-b/build
 cp -a --reflink=auto third_party/gem5-costaware-v3/build/X86_STAGE0 third_party/gem5-costaware-v3-b/build/
fi
cd third_party/gem5-costaware-v3-b
attempt=${1:-B1}
/usr/bin/time -f '%U %S %M' -o ../../continuation_v3/runtime/reports/BUILD_${attempt}.time ../../.venv/bin/scons build/X86_STAGE0/gem5.opt -j2
