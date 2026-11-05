#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
attempt=${1:-A2}
for unit in correctness fault_properties scheduled;do
 /usr/bin/time -f '%U %S %M' -o "continuation_v3/runtime/reports/CPP_BUILD_${attempt}_${unit}.time" g++ -std=c++17 -O2 -Isrc -Isrc/standalone -Ithird_party/gem5/src "src/costaware_v3/${unit}.cpp" build/standalone/tage_base.o -o "build/v3_${unit}"
done
build/v3_correctness
build/v3_fault_properties
