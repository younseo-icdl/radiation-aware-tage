#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
export LD_LIBRARY_PATH="/opt/miniconda3/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
.venv/bin/python scripts/pipeline_v7_prepare.py
cd third_party/gem5-rate-pipeline-v6
/usr/bin/time -f '%U %S %M' -o "../../rate_state_v5_pipeline_v7/runtime/reports/BUILD_${1:-1}.time" ../../.venv/bin/scons build/X86_PIPELINE/gem5.opt -j2
