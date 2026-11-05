#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
export LD_LIBRARY_PATH="/opt/miniconda3/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
.venv/bin/python scripts/v3_prepare_roundc.py
cd third_party/gem5-costaware-v3-c
attempt=${1:-C2}
/usr/bin/time -f '%U %S %M' -o "../../continuation_v3/runtime/reports/BUILD_${attempt}.time" ../../.venv/bin/scons build/X86_STAGE0/gem5.opt -j2
cd ../..
.venv/bin/python - <<'PY'
from scripts.v3_common import *
write(OUT/'reports/BUILD_C_READY.json',dict(status='COMPILED_C',binary_sha256=sha(ROOT/'third_party/gem5-costaware-v3-c/build/X86_STAGE0/gem5.opt'),source_lock_sha256=sha(OUT/'configs/source_C.lock.json')))
PY
