#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
# Shell-local toolchain; no system alternatives/startup changes.
source /opt/rh/gcc-toolset-11/enable
python3 scripts/prepare_tage_standalone.py
g++ -O2 -std=c++17 -Isrc/standalone -Ithird_party/gem5/src -c build/standalone/tage_base.cc -o build/standalone/tage_base.o
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Isources/prior_hw1 -Ithird_party/gem5/src src/tests/predictor_e0.cpp build/standalone/tage_base.o -o build/predictor_e0
./build/predictor_e0
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Isources/prior_hw1 -Ithird_party/gem5/src src/replay/pilot.cpp build/standalone/tage_base.o -o build/pilot
