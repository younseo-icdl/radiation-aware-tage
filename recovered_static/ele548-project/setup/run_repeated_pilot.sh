#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
source /opt/rh/gcc-toolset-11/enable
[[ -f build/standalone/tage_base.o ]] || { echo 'Run setup/run_cpp_stage0.sh first'; exit 2; }
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Ithird_party/gem5/src src/tests/event_stream.cpp build/standalone/tage_base.o -o build/event_stream_test
./build/event_stream_test > reports/event_stream_test.log 2>&1
g++ -O2 -std=c++17 -Isrc -Isrc/standalone -Ithird_party/gem5/src src/replay/repeated.cpp build/standalone/tage_base.o -o build/repeated
.venv/bin/python scripts/run_repeated_pilot.py
