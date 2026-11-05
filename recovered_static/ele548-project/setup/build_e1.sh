#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
[[ -f build/standalone/tage_base.o ]] || { echo 'Run setup/run_cpp_stage0.sh first'; exit 2; }
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Ithird_party/gem5/src src/tests/e1_correctness.cpp build/standalone/tage_base.o -o build/e1_correctness
./build/e1_correctness > reports/e1_correctness.log 2>&1
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Ithird_party/gem5/src src/replay/e1_warmup.cpp build/standalone/tage_base.o -o build/e1_warmup
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Ithird_party/gem5/src src/replay/e1_campaign.cpp build/standalone/tage_base.o -o build/e1_campaign
