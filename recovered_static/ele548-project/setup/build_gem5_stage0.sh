#!/usr/bin/env bash
# Fresh, pinned source, classic-cache X86/O3 only. Preserve older build artifacts.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/rh/gcc-toolset-11/enable
PY_LIBDIR="$("$ROOT/.venv/bin/python" -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR") or "")')"
export LD_LIBRARY_PATH="$PY_LIBDIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
JOBS="${JOBS:-2}"
GEM5_VARIANT="${GEM5_VARIANT:-debug}"
[[ "$GEM5_VARIANT" == debug || "$GEM5_VARIANT" == opt ]] || exit 2
[[ "$JOBS" =~ ^[1-8]$ ]] || { echo 'Use 1..8 jobs; default remains 2'; exit 2; }
# User confirmed no server limits. E3 optimized builds may use 8 workers after
# the measured debug workload pilot; this is a local compiler setting only.
cd "$ROOT/third_party/gem5"
if [[ ! -f build/X86_STAGE0/gem5.build/config ]];then
 "$ROOT/.venv/bin/scons" defconfig build/X86_STAGE0 build_opts/X86
fi
# v25.1.0.1 arch/x86/kvm/SConscript selects X86KvmCPU by KVM_ISA
# even with USE_KVM=n; retain the default module to satisfy its BaseKvmCPU import.
# The actual smoke CPU is X86O3CPU and never executes KVM.
"$ROOT/.venv/bin/scons" setconfig build/X86_STAGE0 RUBY=n USE_SYSTEMC=n USE_KVM=y
"$ROOT/.venv/bin/scons" "build/X86_STAGE0/gem5.$GEM5_VARIANT" -j"$JOBS"
"$ROOT/third_party/gem5/build/X86_STAGE0/gem5.$GEM5_VARIANT" --build-info
