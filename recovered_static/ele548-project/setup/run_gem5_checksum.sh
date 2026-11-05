#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
source /opt/rh/gcc-toolset-11/enable
GEM5_VARIANT="${GEM5_VARIANT:-debug}"
[[ "$GEM5_VARIANT" == debug || "$GEM5_VARIANT" == opt ]] || exit 2
GEM5_BIN="$ROOT/third_party/gem5/build/X86_STAGE0/gem5.$GEM5_VARIANT"
[[ -x "$GEM5_BIN" ]] || { echo 'Build gem5 Stage0 first';exit 2; }
cd "$ROOT"
gcc -O2 -std=c11 workloads/branch_kernel.c -o build/branch_kernel
./build/branch_kernel 20000 > reports/native_checksum.log
gcc -O2 -static -nostdlib -ffreestanding -fno-builtin -fno-stack-protector -no-pie -Wl,--build-id=none workloads/checksum_freestanding.c -o build/checksum_freestanding
./build/checksum_freestanding > reports/native_freestanding_checksum2.log
diff reports/native_checksum.log reports/native_freestanding_checksum2.log
PY_LIBDIR="$("$ROOT/.venv/bin/python" -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR") or "")')"
export LD_LIBRARY_PATH="$PY_LIBDIR${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
timeout 180 "$GEM5_BIN" --outdir=reports/gem5_o3 gem5/o3_checksum.py --binary=build/checksum_freestanding > reports/gem5_o3_checksum.log 2>&1
"$ROOT/.venv/bin/python" - <<'PY'
import hashlib,json,re,configparser
from pathlib import Path
native=Path('reports/native_checksum.log').read_text().strip();log=Path('reports/gem5_o3_checksum.log').read_text()
checks=re.findall(r'^checksum=\d+$',log,re.M)
if checks!=[native]:raise SystemExit('native/gem5 checksum mismatch or missing output')
if 'code: 0' not in log or 'exiting with last active thread context' not in log:raise SystemExit('missing successful gem5 termination')
config=configparser.ConfigParser(interpolation=None);config.optionxform=str;config.read('reports/gem5_o3/config.ini')
cpu=config['system.cpu'];pred=config['system.cpu.branchPred.conditionalBranchPred'];tage=config['system.cpu.branchPred.conditionalBranchPred.tage']
if cpu['type']!='BaseO3CPU' or cpu['decoupledFrontEnd'].lower()!='false' or cpu['numThreads']!='1':raise SystemExit('CPU/frontend config mismatch')
if pred['type']!='TAGE' or tage['type']!='TAGEBase' or tage['nHistoryTables']!='7' or tage['instShiftAmt']!='0':raise SystemExit('plain TAGE config mismatch')
if tage['takenOnlyHistory'].lower()!='false' or tage['speculativeHistUpdate'].lower()!='true':raise SystemExit('history config mismatch')
paths=['build/checksum_freestanding','workloads/checksum_freestanding.c','gem5/o3_checksum.py','reports/gem5_o3/config.ini','reports/gem5_o3/config.json','reports/gem5_o3/stats.txt']
r={'status':'PASS_NATIVE_GEM5_O3_CHECKSUM','checksum':native,'cpu':'X86O3CPU','frontend':'coupled, decoupledFrontEnd=False','conditional_predictor':'plain TAGE','history':'speculative in O3, direction history','rng_seed':548,'radiation_campaign':False,'representative_performance_result':False,'files':{p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in paths}}
Path('reports/gem5_o3_validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
PY
