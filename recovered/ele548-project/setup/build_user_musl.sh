#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/rh/gcc-toolset-11/enable
"$ROOT/.venv/bin/python" "$ROOT/setup/prepare_public_workloads.py"
cd "$ROOT/third_party/musl-1.2.6"
./configure --prefix="$ROOT/.local/musl-1.2.6" --disable-shared CC=/opt/rh/gcc-toolset-11/root/usr/bin/gcc
make -j2
make install
"$ROOT/.local/musl-1.2.6/bin/musl-gcc" --version
