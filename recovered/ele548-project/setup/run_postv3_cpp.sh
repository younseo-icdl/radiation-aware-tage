#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
for unit in promotion_gate correctness fault_properties;do
 /usr/bin/time -f '%U %S %M' -o "postv3/runtime/reports/CPP_FINAL_BUILD_${unit}.time" g++ -std=c++17 -O2 -Isrc -Isrc/standalone -Ithird_party/gem5/src "src/postv3/${unit}.cpp" build/standalone/tage_base.o -o "build/postv3_${unit}"
 /usr/bin/time -f '%U %S %M' -o "postv3/runtime/reports/CPP_FINAL_RUN_${unit}.time" "build/postv3_${unit}"
done
