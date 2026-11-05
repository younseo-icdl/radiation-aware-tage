> 최종 갱신(2026-10-13): namespace v2의 E1/E2/Flying/CERN 고정 예산과 CPU pilot52/main4092/latency687을 모두 완료·검토했다. 최신 완료 상태는 PROJECT_STATUS_AND_REMAINING.ko.md와 SOFTWARE_FINAL_REVIEW.json이다. 아래 재실행 계획·과거 PID는 당시 수정 기록이다.

# Trial RNG namespace 수정과 재실행 — 2026-10-13

검증 중 `master=s+trial`과 `time=s`, `K=s+1`, `location=s+2`의 조합에서 서로 다른 trial/role이 동일 seed를 쓰는 문제를 확인했다. FLYING/CERN의 같은 offset 방식에도 문제가 있었다. 원본 실행 데이터는 유효한 실제 실행 기록으로 보존하지만, independent-trial bootstrap CI를 최종 통계 근거로 쓰지 않는다.

reports/rng_namespace_audit/cross_trial_seed_aliases.json에 구체적 충돌 예시가 있다. 기존 CPU main은548 completed/24 partial outputs 시점에서 이 통계 gate 때문에 중단했다. Observation timeout을 이유로 재시작한 것이 아니다. 종료한 process PID는 stopped_campaign_processes.json에 기록했고 원본 source/config/producer 및 raw logs를 reports/superseded_rng_streams/v1/ARCHIVE_MANIFEST.json과 함께 보관했다.

수정: C++는 master<2^56에서 `(master<<8)|role`로 time1/K2/location3을 분리한다. Existing anchor XOR는 별도 low-byte role22를 만들어 이 세 role과 겹치지 않는다. Python은 PCG64에 SeedSequence[magic,v2,master_lo,master_hi,role,group,occurrence]를 사용한다. 서로 다른 trial/role/record가 다른 namespace를 갖고, 비교 조건 간 의도한 matched owner만 재사용한다. Trial 수/모델/rates/normalizations/workloads/입력/관측창은 변경하지 않았다. Predictor RNG548도 유지한다.

C++ E1/E2 campaign만 sampler seed를 수정·재빌드했다. 실제 gem5 model binary, TAGE 알고리즘과 codec/controller는 변경하지 않았다. Native baseline과 actual O3 correctness gate38은 재사용한다. 새로운 CPU namespace52 pilot이 성공하면 동일4092 main+687 assumed latency와 raw-stat/config audit·report를 자동 진행한다.

수정 E1 design5760과600 warmup sensitivity를 완료했다. `summarize_e1.py --confirm-frozen`은 기존 raw/path+folded346-bit S*를 확인했고 scope file hash dec5020e5a504d0cdf49589e0acc4d2f7e8aa6c61798f61685b468d6dfdefe7b를 그대로 유지했다. Holdout 결과로 보호 범위를 다시 고르지 않는다. 입력 config는 namespace metadata만 바꿨고 design/holdout bytes와 geometry를 모두 검증해 manifest를 rebind했다.

나머지 고정 규모 E2(8184), Flying(2880), CERN(8640), CPU(52+4092+687)를 namespace v2로 실행·검증한다. 현재 상태는 PROJECT_STATUS_SNAPSHOT.json의 live PID와 각 driver log로 확인한다. 이전 보고서에 붙인 superseded gate 표시를 새 corrected summary/evidence로 교체한 뒤 독립 stream CI와 최종 비교를 제시한다. 필수 사용자 조치는 없다.

같은 시점에 CPU audit도 보강했다. Native binary/input 및 pristine stats/config hashes, 실제 stats.txt의 cycles/instructions/committed conditional mispredictions, complete CPU/cache/clock/input configuration, logical manifest 및 atomic event 기록을 직접 확인한다. Bootstrap 입력은 program/trial/seed 순으로 고정해 host 완료 순서가 CI를 바꾸지 않는다.

E4 software interface/activity contract는 sources/e4_software_interface_contract.json과 E4_SOFTWARE_FUNCTIONAL_HANDOFF.ko.md에 있다. Counter는 logical operation proxy이며 P0 word_reads0을 일반 TAGE read activity0으로 해석하지 않는다. 같은 tick의 multiple callbacks는 RTL port/arbitration/throughput 결정과 실제 switching 검증이 필요하다. Cadence/TCAD/RTL PPA를 실행한 결과가 아니다.
