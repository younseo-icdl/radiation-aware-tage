# ELE548 Stage 0 — 2026-10-12

후속 E1 실행 갱신: 5760 design trials와 warmup sensitivity를 완료하고 `raw_path + folded` 346 bits를 S*로 동결했다. 현재 상태는 `E1_REPORT.ko.md`, `E1_SUMMARY.json`, `sources/protection_scope.lock.json`을 우선한다. 아래 Stage0 결과와 그 시점의 UNFROZEN 설명은 초기 실행 기록으로 유지한다.

현재 상태: **E0 기본 M0/CHARM 범위 PASS; Stage0 종료선 완료.** CERN 물리 grouping/모델 fitting은 별도 미완료 gate입니다. TCAD는 사용자 결정으로 사용 불가·범위 제외입니다. 환경 경로 탐지는 실제 EDA license checkout이 아닙니다.

## DONE — 이번 workspace에서 직접 실행한 결과

| 항목 | 결과 | 증거 |
|---|---|---|
| 원본 handoff integrity | 118/118 SHA256 일치 | `original_archive_verification.json` |
| 제공 원문·HW1 reference 보존 | 원본 source manifest 18개 hash 일치 | `source_audit_current.log`, `../sources/manifest.json` |
| 환경 검사·공개 도구 설치 | exec 가능; 별도 `.venv`, gem5 local source 설치 | `environment_audit_run.log`, `user_tools_install.log`, `software.lock.json` |
| Flying Laptop audit | 2129 raw / 2055 distinct records·timestamps / 74 duplicate extras | `data_audit_run.log`, `../data/derived/flying_laptop_audit.json` |
| D01 replay | preserve 2129, collapse timestamp 2055 | `flying_replay_preserve.log`, `flying_replay_collapse.log` |
| CERN 3파일 취득 | 공식 provider MD5 + local SHA256 검증 | `cern_acquisition.json` |
| CERN parser 전수 검사 | p29MeV 1165 / p0.9MeV 7456 / Ar1050MeV 638 clusters | `../data/derived/cern/*.audit.json` |
| CHARM Table II | L06 PDF p13 이미지 확인; 6T 205+9 / 8T 142+5 | `charm_tableII_page13.png`, model card |
| Python tests | 18/18 PASS (제공 15개 + full grammar 3개) | `python_tests_current.log` |
| 제공 C++ tests | protection 636171 checks, Gshare 200000 branches PASS | `cpp_smoke.log` |
| 신규 Gshare adapter | 200000 reference 비교·논리 bit·복사 검증 PASS; 실제 두 warm-up 구간에서도 reference 일치 | `cpp_stage0.log`, pilot logs |
| plain TAGE adapter | 150000 branch direct-upstream differential / complete state·RNG / aging PASS | `cpp_stage0.log`, `tage_source_binding.json` |
| 정확한 주입·snapshot | 65370 logical sites; signed-bit / raw-folded 독립 / duplicate·bounds 원자 거부 / deep-copy·RNG 복원 PASS | `cpp_stage0.log`, logical manifest |
| strict logical manifest | TAGE 65370 sites의 제공 schema 검사 PASS; Gshare 262161 bits의 명시적 compact ID mapping | `logical_manifest_validation.json`, `../sources/tage_fault_sites.jsonl`, `../sources/gshare_logical_state_manifest.json` |
| history buffer rollover | 4096 vs 2097152 buffer의 20000 branch 결과·논리 상태 일치 | `cpp_stage0.log` |
| pilot schedule 재현 | 24-trial repeat 일치, 240개 seed/site/accounting 검증 | `pilot_integrity.json` |
| 새 adapter memory lifecycle | Valgrind 0 errors, 0 outstanding bytes, 14152 allocations/frees | `adapter_valgrind.log` |
| native checksum | libc 및 freestanding 프로그램 모두 `checksum=1321703870693` | `native_checksum.log`, `native_freestanding_checksum2.log` |
| gem5 source build / O3 checksum | v25.1.0.1 debug build PASS; native와 checksum 일치, exit 0; 생성 config 단일 thread/coupled/plain TAGE 검증 | `gem5_build_debug_stage0_attempt2.log`, `gem5_o3_checksum.log`, `gem5_o3_validation.json` |
| 속도 점검 | 24-trial 실행 후 pilot 진행 | `speed_24trials.csv`, `speed_24trials.log` |
| 실제 trace small pilot | 2 workloads × 6 fields × 20 events = 240; 0 failure; wall 0.99s, peak RSS 19424 KiB | `pilot_240trials.csv`, `pilot_240trials.log`, `pilot_summary.json` |

원본 자료의 중복을 MCU로 해석하지 않았습니다. 기존 HW1는 수정하지 않고 새 `src/predictor/`, `src/replay/`, `src/standalone/`에 연구 코드를 만들었습니다. 기존 workspace의 `hw1/ele548_Fall26_HW1.tar.gz`에서 두 실제 trace를 발견했습니다. 추출 provenance/hash와 정확한 범위는 `workload_windows.json`입니다. SHA256SUMS에는 과거 report 파일도 포함되므로 실행 이후 변경된 report의 workspace checksum 실패는 raw source 손상을 뜻하지 않습니다. 원본 ZIP 자체에서 118개를 검증하고 별도 source audit로 불변 자료를 재검증했습니다. 과거 report는 `inherited/`에 보존했습니다.

## 정확성·실험 경계

Preferred source pin은 공식 `https://github.com/gem5/gem5`, **v25.1.0.1 / c8222cc67a399bfc01e8658dd14b30d5bfd634f9**입니다. `tage_base.cc`의 predictor 알고리즘을 직접 컴파일하며 생성 단계는 simulator 통계 constructor 하나만 shim으로 치환합니다. `tage_base.hh`는 upstream 원문을 include합니다. geometry와 schedule은 `../configs/predictor.lock.json`, 제외 상태·logical bits는 `../sources/predictor_logical_state_manifest.json`에 명시했습니다.

Differential은 **공유 upstream 알고리즘의 direct-call reference와 새 adapter의 schedule/state 비교**입니다. 독립 TAGE 알고리즘 재구현이나 O3 전체 동등성 증명은 아닙니다. replay는 predict → branch마다 source와 동일 RNG 연산 → conditional table update → actual history update의 non-spec schedule입니다. CPU는 O3 speculative-history/commit/squash schedule로 별도 검증합니다. CBP4 입력은 실제 branch stream이며 gem5 executable이 아닙니다. `instShiftAmt=0`은 pinned parent default 및 x86 configuration과 일치합니다. 초기 shift=2 시험은 `superseded_shift2/`에 보존하고 최종 수치에서 제외했습니다.

Pilot은 20k conditional-branch warm-up 이후 10k conditional-branch 관측창, field별 bit 균등 표본, conditional ordinal 균등 시점, 1회 persistent XOR입니다. unconditional controls도 TAGE history에 반영했습니다. field별 표본 수가 동일하므로 결과 pooling은 전체 bit exposure가 아닙니다. Warm-up 안정성, 대표성, holdout 성능은 아직 검증하지 않았습니다. Simulator failure를 masked로 세지 않았습니다. Last prediction divergence를 true recovery time이라고 하지 않으며, 종료 시 paired state 차이는 원래 물리 fault 잔존과 구분합니다.

## 데이터/model 카드

`../data/derived/STAGE0_MODEL_CARD.json`을 기준으로 사용합니다. CHARM 두 profile은 별개 categorical multiplicity이고 source 공정→target PDK의 절대 SEU rate로 변환하지 않습니다. Flying Laptop은 detection replay이며 unknown live intervals/bit addresses 때문에 physical arrival process가 아닙니다. CERN parser는 새 파일 전체에서 검증했고 clock label 및 coordinate record ID를 보존했습니다. p29/Ar의 suspected origin sentinel은 원본·all-record audit에 남겨두었습니다. CERN grouping 문헌 및 singleton completeness 확인 전 physical model fitting은 미승인 상태로 유지합니다.

## Gem5 실행 결과와 build 이력

`setup/build_gem5_stage0.sh`와 `setup/run_gem5_checksum.sh`가 최종 PASS했습니다. 실제 executable은 `third_party/gem5/build/X86_STAGE0/gem5.debug`, 실제 CPU config type은 `BaseO3CPU`(Python X86O3CPU), one thread, coupled frontend, plain TAGEBase, 2GHz, classic 32KiB L1I/L1D입니다. Native/O3 checksum은 **1321703870693**, 정상 exit code는 **0**, 종료 tick은 **170216500**입니다. 이는 clean checksum smoke이며 대표 CPU 성능·radiation campaign 결과가 아닙니다. Config와 stats 원본/hash는 `gem5_o3/`, `gem5_o3_validation.json`에 있습니다.

기본 GCC8.5 대신 기존 GCC11을 사용했고 Python shared-library path는 shell-local LIBDIR로 해결했습니다. KVM 비활성화 후 BaseKvmCPU import 오류를 처음 cache 문제로 의심했지만 새 directory에서도 재현됐습니다. Source 확인 결과 `src/arch/x86/kvm/SConscript`는 USE_KVM=n에서도 KVM_ISA=x86이면 X86KvmCPU를 등록하고 `src/cpu/kvm/SConscript`는 BaseKvmCPU를 제외합니다. Fresh-directory 확인 후 KVM build option을 기본값 y로 되돌려 해결했습니다. 실제 CPU는 O3이고 KVM을 실행하지 않습니다. Ruby/SystemC는 build에서 제외했습니다. Stage0는 compile 비용을 줄이는 debug variant를 선택했고, 향후 `GEM5_VARIANT=opt`로 동일 CPU 모델의 최적화 simulator를 만들 수 있습니다. Simulator compiler optimization은 target CPU timing semantics 변경이 아닙니다.

초기 checksum script의 DRAM class typo는 실제 source의 `DDR3_1600_8x8`로 수정해 실행했습니다. 실패 기록은 `gem5_o3_checksum_attempt1.log`, `gem5_o3_checksum_attempt2.log`에 보존합니다. 최종 runtime warnings에는 pydot 미설치, DRAM device capacity 8GiB vs mapped 256MiB, freestanding ELF의 OSABI에 대해 Linux 가정, legacy stats/bucket rounding, GDB socket disable이 있습니다. Freestanding 프로그램은 Linux x86-64 write/exit ABI를 사용하고 native에서 먼저 검증했습니다. 이 경고들을 숨기지 않았으며 일반 Linux benchmark/DRAM 성능 결과로 확대하지 않습니다.

## NOT DONE / BLOCKERS

- ASan: 기본 GCC의 libasan 및 GCC11 sanitizer runtime 부재로 링크 실패. 최대 두 toolchain 시도 후 중단하고 기존 Valgrind로 새 adapter lifecycle을 확인했습니다. ASan PASS라고 표시하지 않습니다.
- 실제 EDA license checkout / PDK / RTL cycle equivalence / PPA / CPU FI hooks: **NOT_RUN**. Cadence activation 사용법은 `/home/youns/ASIC/sram_fft_top`에서 확인했고 사용자 결정으로 실행은 유예했습니다. 초기 Bash PATH 발견만으로 접근 불가를 판정하지 않습니다. 현재 외부 입력 요청은 없습니다.
- 보호방식은 제공 primitive smoke만 검증됐고 **TAGE S*의 P_ED/P_ECC/P_TMR behavior/RTL integration은 아직 구현하지 않았습니다.** 비용·IPC 측정값을 만들지 않았습니다.
- 대규모 캠페인, TAGE-SC-L, 모든 보호방식 RTL, TCAD/Geant4/mission FIT: 시작하지 않았습니다.

## NEXT — 보호 대상을 정하기 위한 근거

작은 pilot에서 raw/path와 folded에서 예측 영향이 주로 관측됐습니다. 상세 harm/help/net과 한계는 `SCOPE_SELECTION_EVIDENCE.md`에 있습니다. **S*는 UNFROZEN**입니다. 다음 승인된 단계에서는 분리된 design data에서 history subfield, inactive table exposure, 긴 잔여 영향 및 CHARM MCU sensitivity를 확인해 상위 1~2 group과 codeword grouping을 동결합니다. 같은 S*에 P0/P_ED(parity+skip/relearn)/P_ECC(SECDED)/P_TMR를 모두 비교합니다. 신규 방법은 기본 세 법 이후 문헌 검토를 거친 선택 확장입니다. E4 same-PDK 실제 latency를 E3 timing에 반영한 후 E5로 통합합니다.

## 재현 명령

```bash
bash setup/check_environment.sh
.venv/bin/python -m unittest discover -s tests -v
make smoke
python3 scripts/audit_flying_laptop.py --csv data/raw/flying_laptop/DetectedSEUTimeTags_with_TLE_Data.csv --out data/derived
python3 scripts/fetch_cern.py
# each acquired file:
python3 scripts/parse_cern_clusters.py --input data/raw/cern/FILE.txt --out data/derived/cern
python3 scripts/prepare_trace_windows.py
bash setup/run_cpp_stage0.sh
.venv/bin/python scripts/qualify_logical_manifests.py
/usr/bin/time -v ./build/pilot 2 548000 reports/speed_24trials.csv
/usr/bin/time -v ./build/pilot 20 548100 reports/pilot_240trials.csv
python3 scripts/summarize_stage0_pilot.py
bash setup/build_gem5_stage0.sh
bash setup/run_gem5_checksum.sh
python3 scripts/audit_stage0_sources.py
.venv/bin/python setup/lock_software.py .
```
