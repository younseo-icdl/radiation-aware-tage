#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
[[ -f build/standalone/tage_base.o ]] || { echo 'Run setup/run_cpp_stage0.sh first'; exit 2; }
mkdir -p reports/e2
g++ -O2 -std=c++17 -Wall -Wextra -Isrc -Isrc/standalone -Ithird_party/gem5/src src/tests/protection_e2.cpp build/standalone/tage_base.o -o build/protection_e2 > reports/e2/build_tests.log 2>&1
./build/protection_e2 > reports/e2_correctness.log 2>&1
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Ithird_party/gem5/src src/replay/e2_manifest.cpp build/standalone/tage_base.o -o build/e2_manifest >> reports/e2/build_tests.log 2>&1
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Ithird_party/gem5/src src/replay/e2_campaign.cpp build/standalone/tage_base.o -o build/e2_campaign >> reports/e2/build_tests.log 2>&1
./build/e2_manifest > sources/e2_stored_sites.csv
