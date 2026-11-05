# Executed Stage0 commands and outcome

| Command | Outcome / log |
|---|---|
| `bash setup/check_environment.sh` | PASS discovery/exec only; `environment_audit_run.log` |
| ZIP SHA256SUMS verification in Python | PASS 118 files; `original_archive_verification.json` |
| `python3 scripts/verify_package.py` after environment reports written | reports differ as expected; `package_verify.log`; immutable ZIP/source audit is authoritative |
| `python3 -m unittest discover -s tests -v` | PASS provided 15; `python_tests.log` |
| `.venv/bin/python -m unittest discover -s tests -v` | PASS current 18; `python_tests_current.log` |
| `make smoke` | PASS; `cpp_smoke.log` |
| `make sanitize` | link FAIL missing libasan; `cpp_sanitize.log` |
| `source /opt/rh/gcc-toolset-11/enable; make sanitize CXX=g++` | link FAIL missing GCC11 sanitizer runtime; `cpp_sanitize_gcc11.log` |
| `bash setup/install_user_tools.sh --apply --python --gem5-source` | PASS isolated venv/source; `user_tools_install.log` |
| `python3 scripts/audit_flying_laptop.py --csv data/raw/flying_laptop/DetectedSEUTimeTags_with_TLE_Data.csv --out data/derived` | PASS exact expected counts; `data_audit_run.log` |
| `python3 scripts/describe_flying_laptop.py` | PASS; `count_profile_run.log` |
| `python3 scripts/generate_schedules.py empirical-detection-replay ...` for each duplicate policy | PASS 2129 and 2055; `flying_replay_*.log` |
| `python3 scripts/fetch_cern.py` | PASS default manifest subset, provider MD5; `cern_download_attempt.log` |
| full-file `scripts/parse_cern_clusters.py` for all 3 files | p29/Ar PASS; p0.9 clock/indexed dialect initially rejected; one documented grammar extension then PASS; `clust_*.parser*.log` |
| `python3 scripts/prepare_trace_windows.py` | PASS actual CBP4 slices; `trace_preparation.log` |
| `bash setup/run_cpp_stage0.sh` | PASS direct upstream correctness; `cpp_stage0.log` |
| `valgrind --error-exitcode=99 --leak-check=full --errors-for-leak-kinds=definite,indirect --track-origins=yes ./build/adapter_memory` | PASS 0 errors/leaks; `adapter_valgrind.log` |
| `./build/pilot 2 548000 ...` then `./build/pilot 20 548100 ...`, measured with `/usr/bin/time -v` | PASS 24 and 240 trials; speed/pilot CSV/logs |
| static-libc build of `branch_kernel.c` | FAIL missing static libc; `native_compile.log` |
| dynamic native `branch_kernel.c` and freestanding x86-64 checksum | PASS same checksum; freestanding initial stack alignment failure fixed using explicit Linux entry alignment; `native_freestanding_checksum2.log` |
| GCC11 `bash setup/build_gem5.sh` | initial Python lib path FAIL; shell-local LIBDIR fix then compile progressed; broad default build intentionally interrupted to remove unused features |
| in-place `scons setconfig build/X86 RUBY=n USE_SYSTEMC=n USE_KVM=n` then build | FAIL embedded KVM module import; initial cache hypothesis disproved by fresh directory |
| `bash setup/build_gem5_stage0.sh` | PASS after KVM module build option restored to default y; CPU remains O3; `gem5_build_debug_stage0_attempt2.log` |
| `bash setup/run_gem5_checksum.sh` | PASS native/O3 checksum and config validation after DRAM class name correction; `gem5_checksum_run3.log`, `gem5_o3_validation.json` |

A build interruption, parser rejection, missing runtime or native crash is never
counted as a successful fault trial. Superseded shift=2 diagnostic outputs are
preserved under `superseded_shift2/`; current pin uses parent default shift=0.
