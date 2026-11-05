# 사용자 조치 — Stage 0 (2026-10-12)

최신 CPU/모델 갱신: 실제 O3 38-case injection/speculation/response gate와 representative 52-run pilot PASS. 고정 CPU main4092와 후속 latency687 runs를 시작했다. Flying Laptop 검출 gap stress는2880 trials PASS이며 duplicates를 MCU로 간주하지 않는다. Software 실행에 SPEC/추가 radiation data/Cadence/TCAD는 요구하지 않는다.

CERN method review에만 최소 추가 source가 있으면 유용하다: DOI `10.1109/REDW51883.2020.9325822`, `10.1109/TNS.2015.2496874`, `10.1109/TNS.2014.2313742`의 접근 가능한 원문 PDF **로컬 경로**. 제공된7편에는 해당 원문이 확인되지 않았다. JYX download/legacy thesis 경로는 restricted/robots, CERN CDS는 bot challenge, HAL `lirmm-01234446`은 Anubis Access Denied, HAL API는 unavailable이었다. 접근 차단을 우회하지 않았다. 이미 취득한3파일 MD5/parser는 유효하지만 grouping/sentinel/singleton 의미를 full-method verified로 표시하지 않는다. 해당 source가 없어도 CPU/CHARM/Flying Laptop 작업은 계속한다. 사용자에게 network/sudo/license 변경을 요청하지 않는다.

최신 E2/E3 갱신: 동일 S*의 네 설계 C++ 구현·정상/오류 검증과 holdout 8184 trials를 완료했다. 신규 SPEC 설치 또는 dataset 업로드 요청은 없다. 공식 MiBench 3개 프로그램과 입력을 취득하고 user-local musl로 static ELF를 빌드했으며 independent native 정답과 O3 clean baseline을 통과했다. 실제 cycles/IPC는 `E3_PUBLIC_CLEAN_BASELINE.ko.md`에 있다. CPU FI/보호 timing 비교는 다음 단계다. Debug 2개 timeout은 optimized 동일 입력 재실행으로 해결했으며 사용자 조치 요청은 없다. 아래 E1/Stage0 항목은 당시의 기록이다.

E1 갱신: 사용자가 HW1 데이터로 진행, 서버 제한 없음, PDK/Cadence 검토 유예를 확인했다. 5760 design trials 및 추가 warmup sensitivity를 완료했고 `raw_path + folded` 346 bits를 S*로 동결했다. 현재 software 작업에 신규 SPEC/외부 dataset 또는 사용자 수동 검증 요청은 없다. 사용 자료는 CBP trace 및 SPEC2006 유래 trace로 명시한다. 다음은 같은 S*의 E2 세 recovery controller와 holdout 평가이고, CPU cycles/IPC는 별도 gem5 E3에서 측정한다. 최신 결과는 `E1_REPORT.ko.md`를 참고한다.

최신 전체 상태와 남은 실험은 [PROJECT_STATUS_AND_REMAINING.ko.md](PROJECT_STATUS_AND_REMAINING.ko.md)를 우선합니다. 지금 HW1 기반 E1/E2와 공개 workload CPU 준비에 필수 미제공 파일은 없습니다. SPEC 항목은 실제 SPEC application 추가 시의 조건이며 현재 필수 설치 요청이 아닙니다. 사용자 확인 항목은 교수님 요구/재사용 범위, 추가 자원·일정 제약, E1 후 S*와 이후 CPU/PPA 비교 범위 검토입니다.

현재 C++ SEU 실행에 외부 radiation dataset 업로드나 TCAD는 필요하지 않습니다. TCAD는 사용자 결정에 따라 사용 불가·연구 의존성에서 제외했습니다. CERN 3개 파일은 취득/MD5/전수 parser 검증을 완료했고 실제 HW1 trace 구간도 확보했습니다. SPEC CPU track의 별도 준비 항목은 아래에 기록했습니다.

반복 주입 갱신: Poisson/CHARM C++ continuous-state pilot 96 runs + 1 determinism regression PASS. 추가 dataset 없이 실행했으며 현재 SEU 작업에 사용자 조치는 없습니다. E3의 tick hook과 E4의 최종 비교는 아직 완료하지 않았습니다. S* 선정/E2 구현이 남아 있고 Cadence 실행은 기존 결정대로 유예했습니다. `E3_E4_READINESS.ko.md`와 `DATASET_READINESS.json`에 구체 조건을 기록했습니다.

## HW1 자료만으로 진행 가능한 범위

원본 archive를 재확인했습니다. 총 40개 trace에 `LONG-SPEC2K6-00..19` 20개가 있으며 CBP 공식 설명에서 SPEC 2006 유래임을 확인했습니다. E1/E2의 predictor 오류·회복 실험은 이 자료로 진행 가능하며 **이 경로에 신규 SPEC 설치는 필요하지 않습니다.** 기존 pilot은 SHORT-INT-1/SHORT-FP-1 구간을 사용했습니다.

archive의 `sim.bin`은 `../sim/predictor`를 복사한 trace evaluator이고 SPEC application binary가 아닙니다. 원본 record에는 PC/target/opType/taken만 있으며 full CPU 실행에 필요한 instruction bytes/register operands/data addresses 등은 없습니다. E3의 cycles/IPC는 실제 application binary/input으로 검증하며 공개 workload로 진행할 수 있습니다. 아래 SPEC 접근 항목은 **SPEC application을 gem5에서 실행하려는 경우의 별도 경로**이고 지금 E1/E2나 공개 workload E3를 막는 prerequisite가 아닙니다. 증거: `HW1_WORKLOAD_CAPABILITIES.json`, [CBP 공식 framework](https://jilp.org/cbp2014/framework.html).

## SPEC CPU — 설치본 미보유, 학교 접근 여부 확인 필요

사용자가 2026-10-12에 SPEC를 아직 설치하지 않았다고 확인했습니다. 이것은 실행 실패가 아니라 **NOT_INSTALLED / LICENSED_DISTRIBUTION_NOT_PROVIDED**입니다. 다운로드·구매·SPEC 실행 명령은 아직 수행하지 않았습니다. SPEC는 라이선스가 있는 software이므로 사용 권한이 확인되지 않은 배포본을 취득하지 않습니다.

필요한 최소 사용자 항목: 학교/연구실에 사용 가능한 SPEC CPU가 있는지 확인하고, 있다면 버전과 ISO/tar/shared installation 경로를 알려주십시오. 설치/compile/native output 검증/gem5 실행은 Codex가 담당합니다. 사용자에게 수동 compiler·주입 검사를 요청하지 않습니다. 구매나 관리자 권한을 요청하는 단계가 아닙니다.

SPEC access 전에도 기존 C++ E1/E2와 공개 benchmark의 CPU baseline, P0 gem5 hook 작업은 계속할 수 있습니다. `NON_CADENCE_EXPERIMENTS.ko.md`에 실험·검증 분담과 CPU 비교 지표를 기록했습니다. 공식 근거: [SPEC Unix 설치 안내](https://www.spec.org/cpu2017/Docs/install-guide-unix.html) (licensed software 및 기관 내 설치 조건).

## Cadence — 사용자 결정으로 E4 유예, 현재 조치 요청 없음

사용법은 `/home/youns/ASIC/sram_fft_top/.cursor/rules/cadence-tools.mdc`와 `AGENTS.md`에서 확인했습니다. 핵심은 **C-shell에서 `cadence-activate`를 실행**하는 것입니다. 초기 Bash PATH 검사만으로 활성화 방법을 사용자에게 다시 요청한 부분을 수정합니다. 기존 PDK/library/LEF 설정은 `blocks/fft_top_baseline_b/pnr/common/lib_setup.tcl` 등 해당 repo flow에 있습니다. 실제 경로 존재·tool version·license checkout은 E4 재개 시 확인합니다. 이번에는 Cadence를 실행하지 않았습니다.

현재 SEU 모델링·C++ 주입에는 사용자 입력이 필요하지 않습니다. 다음 단계는 `NEXT_SEU_STEPS.ko.md`에 정리했습니다. E4에서는 선택한 library/PVT/clock/load와 기능을 네 설계에 공통으로 고정합니다.

## Sanitizer runtime (선택 조치)

`make sanitize`는 기본 GCC 8.5에서 `/usr/lib64/libasan.so.5.0.0` 부재로 링크 실패했습니다. shell-local GCC 11 toolset으로 한 번 재시도했지만 `libasan_preinit.o`/`-lasan`이 없습니다. 기존 환경을 변경하지 않았습니다. 기존 Valgrind로 새 adapter의 allocation/copy/injection lifecycle을 별도 검사합니다. ASan 결과가 꼭 필요하면 관리자에게 GCC 11 sanitizer runtime 또는 이미 설치된 sanitizer 지원 compiler 경로만 요청하면 됩니다.

## gem5

정확한 pin은 `v25.1.0.1` / `c8222cc67a399bfc01e8658dd14b30d5bfd634f9`입니다. GCC 11 toolset은 이미 발견해 사용했으므로 compiler 설치 요청은 없습니다. 첫 configure는 Python shared-library 경로 누락으로 실패했고, 현재 shell에 `/opt/miniconda3/lib`를 추가해 configure를 통과했습니다. KVM 비활성화 시 `BaseKvmCPU` import 오류가 새 directory에서도 재현됐습니다. 해당 pinned SConscript의 상속/module 등록 조건을 확인해 KVM build option은 기본값 y로 유지하며 새 `build/X86_STAGE0`에서 Ruby/SystemC 제외 구성을 빌드합니다. 실제 CPU는 O3이며 KVM을 실행하지 않습니다. Stage0 checksum에는 `gem5.debug` variant를 사용하며 CPU 모델은 X86 O3입니다. 최종 build와 native/O3 checksum은 **PASS**이며 종료 코드 0을 확인했습니다. gem5에 대한 현재 사용자 조치는 없습니다. Config/run logs는 `STAGE0_REPORT.md`와 `VALIDATION_STATUS.json`을 참조하십시오.
