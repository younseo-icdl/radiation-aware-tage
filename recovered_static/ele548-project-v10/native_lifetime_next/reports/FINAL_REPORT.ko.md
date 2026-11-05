# Native R1/R8 후속 비교 — 실제108회 완료

## 결정

**IMPLEMENTED/TESTED RESULT:** 정상36+오류72회가 모두 실행·정답 gate를 통과했다. 원시1836파일 SHA, 여섯 independent owner tape, 72 matched A/B/C/D를 검증했다. 기존R2 실행/source/config/binary/결과를 보존했다. 이번 비교는 공개 MiBench qsort·dijkstra·sha1이며 SPEC CPU 실행이 아니다.

**NEW DERIVATION:** 실행창이 길어진 R8에서 무보호의 누적 오류 증가분이 커진 사례가 관측됐다. Exact direct는 이 조건에서 무보호 대비 이득이 있지만, 모든 기존 보호보다 빠르지는 않다. Dijkstra와sha1에서 direct/ECC/TMR의 오류 증가 cycles는 모두0이었다. Qsort에서는 parity가 더 빠른 조건도 있었다. 사건으로 생긴 성능 개선도 삭제하지 않았다.

**ASSUMPTION / 미확정:** C0는 정상 check/encode/vote/source/transport가 현재 stage에 들어간다는 가정이다. 실제 normal 보호 overhead가0임을 측정한 결과가 아니다. 프로그램당 owner2이므로 아래 숫자는 탐색적 관측이며 population 우위나 동등성을 증명하지 않는다. 현재 하드웨어 qualified 후보는0개다.

## 무엇을 고정하고 실행했나

- 별도 `codex/v10-history-cost` worktree의 `native_lifetime_next` producer/output을 사용했다. 기존 gem5/program ELF를 재빌드하지 않았다.
- 고정 S*=346bit의 P0/P_ED/P_ECC/P_TMR을 유지하고, frequent parity와 periodic incremental parity(k64), exact direct를 포함한 총6방식을 비교했다.
- R1/R8은 동일 persistent program에서 작업1회/8회를 수행한다. CPU/cache/allocator/predictor 상태가 이어진다. 제어파일/prologue와 실제 branch stream은 R에 따라 다를 수 있다.
- 각 프로그램의 실제 U/R1 정상 cycles H를 얻은 뒤 tick을1..H×500에서 균일 추출하고 논리 raw130 age0..129를 균일 추출했다. 이는 **조건부 single-SBU 실험 가정**이다. CHARM/Poisson 도착rate 또는 방사선 측정 bit-flip rate를 추정한 것이 아니다.
- 프로그램당 새 owner2개, 총6개의 event time/location RNG namespace-v2를 분리 고정했다. 같은 owner/tick/site를 R1/R8과여섯 방식에 재사용했다. 72replay를72독립 표본으로 세지 않는다.
- native L0/C0, LEGACY resource와500ticks/cycle 계약을 유지했다. U/direct는 P0·repair0이고 기존 네 보호법은 repair4다. 보호의 functional repair 뒤 hold 모델은 실제 직렬 RMW 구현과 같다는 주장이 아니다.
- 이번 노출은 SOURCE raw130뿐이다. path/fold와추가 metadata를 포함한 WHOLE 노출은 기존R2와 구분하며, 이번 통과를 metadata/전체 predictor 안전성으로 확대하지 않는다.

## 정상 CPU 결과

같은 프로그램/R 안에서 여섯 방식의 cycles·instructions·canonical predictor state·predictor RNG가 모두 같았다. 이 검증은 알고리즘/실행의 정상 동일성이다.

|프로그램|R|cycles|IPC|
|---|---:|---:|---:|
|qsort|1|5,436,009|0.783800|
|qsort|8|43,206,272|0.788115|
|dijkstra|1|14,715,853|1.054599|
|dijkstra|8|117,040,391|1.060308|
|sha1|1|2,504,054|1.952126|
|sha1|8|19,651,079|1.988175|

## 오류 후 CPU 결과

A/B=정상/오류 무보호, C/D=정상/오류 후보 cycles다. 아래 R8 값은 두 owner의 `100(B−D)/A` 평균이다. 양수는 해당 조건에서 보호 후보가 오류 무보호보다 적은 cycles를 사용했다는 뜻이다. 정상 성분 `(A−C)`와 오류 증가분 차이를 별도 CSV로 보존했다.

|R8 순이득 (% of A)|P0|frequent P_ED|periodic P_ED k64|SECDED|TMR|exact direct|
|---|---:|---:|---:|---:|---:|---:|
|qsort|0|1.053572|1.034304|1.024613|1.024613|1.032251|
|dijkstra|0|1.204594|1.204594|1.210535|1.210535|1.210535|
|sha1|0|0.734881|0.734881|0.722286|0.722286|0.722286|

- Qsort R1의 direct는 기존 네 보호보다 평균0.033876~0.036249 percentage points 느렸다. R8에서는 ECC/TMR보다 평균0.007638pp 빠르지만 frequent parity보다0.021321pp, periodic parity보다0.002053pp 느렸다. R8 대조의 관측 owner 범위는 양·음수를 포함한다.
- Dijkstra의 direct/ECC/TMR은 두 R에서 모두 동일 cycles였다. R8 parity의 평균 오류 증가분은6,953.5cycles였고 direct의 parity 대비 평균 이득은0.005941pp였다. 동일 관측은 모집단 동등성 증명이 아니다.
- Sha1의 direct/ECC/TMR도 두 R에서 동일 cycles였다. Direct의 parity 대비 평균 이득은 R1에서 약0.112pp였지만 R8에서는−0.012595pp였다. Parity 경로에서 관측된 음의 오류 증가분도 유지했다. 재학습·fallback의 인과 기여를 분해한 결과는 아니다.

R1/R8 전체36개 cell, 모든4 conventional 대조, owner별 signed 값과 empirical 구간은 `analysis/final/REPORT.ko.md`, `CPU_ABCD.csv`, `DIRECT_CONTRAST_SUMMARY.csv`에 있다. n2 exact empirical bootstrap2.5/97.5% endpoints는 관측 두 값의 min/max이며 formal95% coverage/비열등성/동등성 근거가 아니다. 사후 최소값을 고르는 배포 정책을 만들지 않았다.

### 같은 cycles와 상태 회복의 구분

**IMPLEMENTED/TESTED RESULT:** R1/R8를 합친 direct12행 중8행은 D=C였지만, 그중3행은 종료 canonical base-state hash가 자체 clean과 달랐다(dijkstra R1 owner0, sha1 R1/R8 owner0). ECC/TMR은 각각12행 모두 D=C와 canonical hash 일치였다. Hash 일치는 fingerprint 일치이며 전체 저장소의 exhaustive bit-equality 증명은 아니다.

**SOURCE FACT:** direct의 canonical hash는 실제 direct raw/path와 재계산한 folds를 사용한다. 사용하지 않는 recurrent fold register만의 차이로 위 hash 불일치를 설명할 수 없다. Hash는 bimodal/tagged table·raw/path/fold와일부 TAGE metadata를 포함하지만 추가 보호/endpoint storage·rollback-only journal·explicit head·RNG는 제외한다. 불일치한 canonical component는 아직 국소화하지 않았다. [고정 v9r2 소스의 hash 구성](/home/youns/workspace/ele548-project-v9/third_party/gem5-native-v9r2/src/cpu/pred/research_native_v9r2_tage.cc:269).

별도 `fold_phi_mismatch_words`는 direct에서 inactive recurrent helper의 일관성 진단이므로 active direct folding 손상으로 해석하지 않는다. 성능 피해를 줄이는 목표와 상태 완전 동일성은 다른 판정이며, zero cycles로 미래 무해나 종료 이후 회복을 주장하지 않는다.

## 긴 유지창에서 무엇이 달라졌나

|무보호 평균 오류 증가분 B−A (cycles)|R1|R8|R8−R1|
|---|---:|---:|---:|
|qsort|46,921|442,697|395,776|
|dijkstra|5,905.5|1,416,815|1,410,909.5|
|sha1|4,504.5|141,937|137,432.5|

같은 owner의 `[D8−C8]−[D1−C1]`은 누적 horizon contrast다. 같은 tick/site도 R별 주입 직전 history/cache/branch 상태가 같음을 보장하지 않는다. 추가 작업만의 damage kernel·적분·정확한 회복 시간이나 source/fold/table별 인과 비율로 해석하지 않는다. 비율 차이에는 A8/A1 분모의 희석이 섞일 수 있어 절대 cycles를 우선한다. task 경계 marker와 bit discrepancy snapshot은 이번에 추가하지 않았다. R8/프로그램 종료 이후 tail은 UNKNOWN이다.

도표는 `plots/final/FAULT_INCREMENT_CYCLES.png`와 `NET_GAIN_PERCENT.png`이며 PDF도 함께 제공한다. 두 owner 점과 평균을 분리하고, 같은 프로그램의 R1/R8 y축 범위를 같게 했다. 모집단 CI를 그리지 않았다.

## 비용 연구와 연결한 다음 결정

**이전 별도 component 결과:** `cost_v10/reports/FINAL_REPORT.ko.md`는 실제 fold 저장/update 비용과 TT/SS timing을 다룬다. 저장200bit를 포함한 recurrent boundary와 stateless direct boundary의 mapped cell area는962.640/641.466µm²였다. 이는 약33.36% component 면적 차이이며 전체 보호 macro/CPU PPA나 SEU 단면적 차이가 아니다. 기존 SS-cell/typRC direct lookup의 setup 위반도 보존했다. 서로 다른 worst path를 빼서 lookup 차이라고 부르지 않는다.

**DESIGN HYPOTHESIS:** update-time full-fold overwrite는 저장된 fold의 이전 오류 의존성을 끊으면서 registered read를 유지할 수 있는 다음 통합 후보1개다. 현재 C++/RTL 소형 primitive gate만 통과했으며 gem5/전체 source·ownership·rollback controller/PPA 결과는 없다. 이번108회에서 이를 시험했다고 표시하지 않는다.

다음 우선순위는 많은 C0 seed만 추가하는 것보다, 해당 후보의 정확한 operand sampling·speculative undo·freshness·source 검증·유한 ports/queue 계약을 CPU에 통합해 정상 비용과 오류 후 비용을 함께 측정하는 것이다. 후보/입력/owner를 고정한 뒤 독립 평가해야 한다. 기존6방식은 계속 비교군으로 유지한다. Direct 우위나 신규 후보 성공을 가정하지 않는다.

`review/NEXT_ROUND_BUDGET_OPTIONS.ko.md`에 실제 정상 시간에 근거한 두 계획을 남겼다. 새 후보의 최소 계획은 dev18 replication + independent evaluation126 + reserve6=최대150회다. 현재3469에서 전부 실행하면 cap3619가 필요하고, 기존3475 대비 증액은144회다. 시간 proxy13.1469coreh는 새 입력/새 알고리즘/build 비용을 포함하지 않아 승인 상한이 아니다. 별도 source/build의 disk도 UNKNOWN이며 현재8GiB 여유로 충분하다고 가정하지 않는다. 추가 실행·예산 변경은 하지 않았다.

## DONE — 명령과 증거

1. `runtime/configs/BUDGET_AMENDMENT.lock.json`: 사용자 원문 `3,475회·16 core-hours로 확대하고 진행`, plan/prepared/producer SHA 연결.
2. `tools/run_approved_batch.py`: tmux에서 clean → fault-plan → fault 순서; `runtime/reports/BATCH_DRIVER.json`의3phase 모두exit0. 초기 gate/pilot 뒤 공유32slots 사용.
3. `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -B native_lifetime_next/tools/analyze_lifetime.py --out-dir native_lifetime_next/analysis/final`: 실제108/valid72/raw1836 PASS.
4. 같은 thread 제한의 `tools/plot_lifetime.py --analysis-dir .../analysis/final --out-dir .../plots/final`: PNG/PDF 및 SHA-bound `PLOT.lock.json` 생성, net gain 그림을 시각 검사했다.
5. 독립 terminal 재검산 FIX1이72 ABCD·48 paired direct 대조·36 summary·18 horizon summary와 raw1836 SHA를 실제 재검산해 PASS했다. 증거는 `review/TERMINAL_STATISTICAL_AUDIT.*`다. 최종 count/hash/시간/보존 gate는 `reports/FINAL_GATES.json`과 `RESOURCE_ACCOUNTING.json`에 기록한다. Gate가 없으면 최종 provenance/resource acceptance가 완료되지 않은 것이다.
6. Private delta archive의 CRC/전체 payload SHA/실제 packaging 후 disk는 `POST_PACKAGE_VERIFICATION.json`에 기록한다. 기존 component ZIP은 유지한다. ELF/PDK/library/DB/논문/전체 environment는 새 archive에 포함하지 않는다.

## 실패·경고와 자원

- 실제 gem5 실행 실패0, timeout0, orphan/unrecorded0; 정상36/오류72 모두 정답 일치. 검증된 fd1 regular stdout의 `TIOCGWINSZ→ENOTTY` 호환 경고는108회 원문을 유지했다. 실제 native6 strace와 pinned handler가 같은 반환 의미임을 검증했으며 일반 unsupported syscall 허용이 아니다. 다른 unknown unsupported 경고는0이다.
- 실행 중 수동 selfcheck는 미완성 GNUtime을 발견해 fail-closed했다. 실행을 변경하지 않았고 simulator failure/masked fault로 세지 않았다. 이 관측 제한은 `RESUME.ko.md`에 남겼다.
- 독립 terminal 검산 A1은 direct에도 repair4를 기대한 검산 코드의 가정 오류로 중단됐다. 실제 U/direct P0의 repair0에 맞게 검산 기대값만 수정했다. A1 시간/비정상 종료는 보존했고 CPU 결과나 producer를 수정하지 않았다. 수정 후 실제 검산 상태는 `review/TERMINAL_STATISTICAL_AUDIT.json`에서 확인한다.
- CPU actual3469/3475, 이번108, reserve6미사용이다. 완료된 GNUtime 기록은 후속 약5.54coreh, v9+component+후속 약11.17/16, 전체 약76.57/108coreh다. 최종 원본 path/SHA/초 및 native outer/child 중복 제외는 `RESOURCE_ACCOUNTING.json`이 권위 있는 정밀 기록이다. 이는 기록된 process-tree 시간이며 server 전체 사용량 측정이 아니다.
- 최종 disk는 archive 생성 후 `POST_PACKAGE_VERIFICATION.json`으로 재측정한다. 후속384MiB/component512MiB/v9+new8GiB/전체34GiB/free10GiB 제한을 유지한다.

## NOT DONE / BLOCKERS / NEXT

NOT DONE: 실제 전체 stage timing/energy/PPA, mission FIT/SEU per-bit calibration, WHOLE 신규평가, task별 damage kernel/tail, overwrite의 CPU 통합, 추가 독립 입력/owner 평가. 이번 단계에서 새 RTL/Cadence/SPICE/TCAD를 실행하지 않았다.

BLOCKERS: primary108 실행·정답 단계 blocker는 없다. 새 round의 complete paired 계획은 남은 reserve6으로 실행할 수 없으며 build/source disk와 시간 admission을 별도로 정해야 한다. 이를 환경·license 실패로 표시하지 않는다.

NEXT: terminal 검산과 final evidence/archive gate를 완료하고 현재 round를 닫는다. 다음 round를 시작할 때 위 최소 계획과 source/build 실측 gate를 먼저 고정한다. 성공 여부는 실제 비용을 포함해 판단하며 하드웨어 승자를 강제로 선정하지 않는다.
