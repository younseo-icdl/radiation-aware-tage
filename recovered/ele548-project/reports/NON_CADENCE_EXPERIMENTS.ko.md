# Cadence 제외 실험·검증 분담 — 2026-10-12

최신 실행 갱신: E0/E1 및 E2 세 recovery controller/SBU·CHARM holdout 8184 trials를 완료했다. `E2_REPORT.ko.md`를 우선한다. 공개 MiBench 3개 native 정답 및 O3 clean baseline을 완료했고 실제 cycles/IPC는 `E3_PUBLIC_CLEAN_BASELINE.ko.md`에 있다. CPU fault injection/speculation/rollback/latency 비교는 다음 단계다. 아래 표의 E1/E2/CPU baseline 미완료 표기는 최초 계획의 기록이다.

## 지금 수행할 실험

| 순서 | 실험 | 확인하려는 것 | 상태 / 담당 |
|---|---|---|---|
| 1 | Single-event E1: 같은 post-event 길이, warmup/window 변화, 여섯 field 및 raw/path·folded subfields | 상태별 harm/help/net, 첫 영향, 잔여 상태, 관측끝 censoring; 어떤 S*를 보호할지 | 작은 pilot만 PASS. 입력/seed split과 예산을 고정해 Codex가 수행 |
| 2 | 반복 주입: SBU/CHARM, event-rate와 expected-flip-rate를 각각 매칭, 검증 후 CERN footprint·Flying Laptop time sensitivity | 사건 간격·군집이 누적 영향과 보호 선택을 바꾸는지 | Poisson/CHARM P0 96-run engineering pilot PASS. main/model uncertainty 검증은 Codex가 수행 |
| 3 | S*를 design data에서 동결하고 같은 S*의 P0/ED/ECC/TMR 구현·비교 | no-fault 기능, 실제 detection/fallback/relearn/writeback/vote/repair, added storage exposure | TAGE integration NOT_RUN. Codex 담당 |
| 병행 | Representative program의 native와 gem5 O3 clean baseline | 정답, 지원 syscall/ISA, ROI, warmup, 정상 cycles/IPC/committed-branch MPKI, 실행 예산 | checksum만 PASS. SPEC 준비와 공개 workload 작업을 E1과 병행 가능 |
| 병행 | P0의 gem5 logical-state hook와 SimTick 주입 smoke | zero/one/repeated fault, current raw와 folded 독립 주입, same-tick ordering, speculation/squash | NOT_RUN. S* 확정 전 기반 검증 가능. Codex 담당 |
| E2 이후 | 같은 CPU workload의 clean/faulty × P0/ED/ECC/TMR | 오류 성능 손실 감소와 정상시 보호 overhead를 모두 포함한 총 효과 | NOT_RUN. Codex 담당 |

CERN은 현재 세 파일의 MD5/전수 parser가 통과했지만 cluster/sentinel/singleton 의미 검토가 남았다. 이것 때문에 CHARM 기반 실험이나 CPU clean baseline을 멈출 필요는 없다. 원본 Flying Laptop duplicate를 MCU 크기로 바꾸지 않는다.

## CPU 성능 실험 계약

- 대표 program 2~3개부터 source/license/input/compiler/binary hash, argv/stdin, 정상 output validation과 ROI를 고정한다. 실제 E3 성능은 실행 binary를 gem5 O3에 넣어 측정한다. 기존 HW1 branch trace는 C++ replay 입력이며 SE-mode executable이 아니다.
- 먼저 native와 동일 binary의 gem5 결과를 검증한다. SPEC이면 해당 입력의 reference/공식 validation 규칙도 적용한다. test input과 짧은 kernel은 호환성 smoke이며 representative 성능 결과와 구분한다.
- single-core/single-thread, coupled frontend, plain TAGE, 같은 CPU clock/cache/width/compiler/input/ROI를 유지한다. CPU metric은 simulator cycles/ticks이고 host wall time은 연구 runtime이다.
- 모든 설계에서 clean twin을 보존한다. A=P0 clean, B=P0 faulty, C=Pi clean, D=Pi faulty를 측정한다. B-A는 무보호 fault loss, C-A는 clean protection overhead, D-C는 보호후 fault loss, B-D는 같은 workload의 총 cycles 이득이다. 다른 fault seed/모델/노출 조건을 섞어 직접 비교하지 않는다.
- committed instructions/branches를 기준으로 IPC 및 MPKI를 계산한다. wrong-path의 lookup 수/복원 동작은 별도 보조 지표다. assertion, checksum mismatch, timeout, unsupported syscall은 failure class이며 masked fault가 아니다.
- E3는 tick/cycle 기반 사건을 사용한다. 같은 work 종료까지 외부 event clock이 계속 진행하여 느려진 설계의 추가 노출을 허용한다. C++ events/conditional branch를 그대로 events/second로 표기하지 않는다.
- Cadence 전에도 CPU fault effect와 명시적 check/repair latency 가정의 sensitivity를 실험할 수 있다. 이를 실제 RTL latency로 부르지 않는다. 최종 hardware 비용을 포함한 ranking은 E4 측정 delay/energy를 반영한 뒤 확정한다. 추가 latency는 실제 predictor response/ready/hold/redirect 경로에서 모델링하며 misprediction penalty 하나를 바꾸는 것으로 대체하지 않는다.
- full predictor checkpoint serialization이 검증되지 않으면 매 run warmup을 재실행한다. 초기 CPU trial 시간/메모리를 측정한 뒤 seed 수와 예산을 사전에 고정한다.

## SPEC 준비와 사용자 항목

사용자는 2026-10-12에 SPEC 설치본이 아직 없다고 확인했다. **SPEC 프로그램으로 평가하려면 사용 권한이 있는 배포본/공유 설치본을 먼저 확보해야 한다.** gem5의 설치나 HW1 trace archive에 SPEC suite가 포함된 것은 아니다.

사용자에게 필요한 항목은 학교/연구실의 SPEC CPU 라이선스·사용 권한과 CPU 2006/2017 등 버전, 접근 가능한 ISO/tar/shared installation 경로 확인이다. 현재 새 구매, 관리자 권한, 시스템 변경을 요청하지 않는다. SPEC access가 마련되면 Codex가 사용자 workspace의 별도 위치에서 설치/compile/native validation/gem5 실행을 수행한다. 공개 workload 검증과 E1/E2/P0 hook 작업은 그동안 계속 가능하다.

사용자가 수동으로 compiler/RNG/각 flip/rollback를 검증할 필요는 없다. Codex가 tests, seeds/schedules, 명령, 원 로그와 결과를 보존한다. 사용자는 최종 결과의 workload/input/ROI가 연구 목적에 맞는지, 같은 S*와 CPU 조건에서 비교했는지, confidence와 실제 가정 범위가 표기됐는지를 검토하면 된다. 교수님이 특정 SPEC 버전이나 application을 요구했다면 그 제약만 추가로 알려주면 된다.

SPEC 공식 출처: [CPU 2017 overview](https://www.spec.org/cpu2017/Docs/overview.html), [Unix install guide](https://www.spec.org/cpu2017/Docs/install-guide-unix.html). 선택한 일부 program/ROI의 simulated cycles·IPC 비교를 공식 suite 전체의 SPEC score로 표시하지 않는다.
