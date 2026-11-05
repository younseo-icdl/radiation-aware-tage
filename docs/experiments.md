# Experiment protocol

## Correctness before measurement

Run `make test` before a new experiment producer. The suite checks:

- Plain-TAGE adapter equivalence to direct backend calls, full state and RNG continuity, usefulness aging, signed-bit encoding, snapshot/deep copy, raw/fold independence, event atomicity, and history-buffer rollover.
- SECDED single-error correction and double-error detection, real higher-order decoder failures, parity even-bit misses, correlated TMR failures, and actual-outcome refill.
- Finite source/lookup requests, independent-request throughput, queue-full backpressure, squash/cancel, stale-response rejection, epoch wrap, source head/FIFO metadata faults, actual commit ingress, and mid-RMW injection.
- Radiation source parsers, namespace separation, schedule laws, paired statistics, and end-to-end replay.

Component tests do not execute an O3 workload. After a gem5 integration change, run the checksum under native and finite configurations and compare its output. Record program termination and helper-drain validation as separate checks. Wrong output, crashes, unresolved metadata, and timeout remain explicit outcomes.

## Single events and repeated exposure

First use single-event trials to estimate role-specific conditional sensitivity. Sample injection time and logical bit, retain the damaged state, and compare clean/faulty execution. A single event is not an estimate of a per-second radiation rate.

Then use repeated events from a declared arrival/mark process without resetting state between events. This captures natural recovery, learning contamination, error overlap, and repair contention. Freeze schedule generation independently of candidate performance and declare the time coordinate. Preserve atomic K-bit events.

Report SOURCE(raw130), fixed SSTAR346, and WHOLE(manifest exposure) separately. Raw and folded faults may propagate differently; do not automatically recompute folds when injecting a raw bit. Exact direct has no authoritative recurrent fold cells, so a missing fold target is not a successfully repaired fault.

## CPU comparisons

Keep the original native timing path as a clean reference, then compare finite P0 and protection candidates under the same query/update latencies, II, ports, and finite capacities. Recurrent P0/P_ED/P_ECC/P_TMR, periodic parity, and exact direct are supported finite configurations.

A common finite reference deliberately charges matched stages to P0. Report its clean overhead relative to native separately from protected-minus-finite-P0 overhead. Software stage-fit assumptions are not measured hardware costs. Never use a single-pending latency sensitivity as the performance of a pipeline.

Collect program-specific cycles, IPC, actual issued/consumed requests, maximum outstanding requests, and source/dependency/queue/response stalls. Stall counters can overlap; their sum is not an exact CPI decomposition. Separate independent-request component throughput from actual branch-stream throughput with next-PC/history dependencies.

Program output must match the clean reference. An SEU event is not allowed to relax the program's correct answer. Performance is frozen at architectural program exit. Finite helper completion may be checked afterward with event exposure and architectural counters held fixed; that observation time is not added to workload cycles.

## A/B/C/D and paired owners

| Cell | Faults | Protection |
|---|---|---|
| A | None | P0 |
| B | Declared schedule | P0 |
| C | None | Candidate |
| D | Matched schedule | Candidate |

The CPU cycle net benefit is **B-D**. Also report clean cost C-A, unprotected fault penalty B-A, and residual protected penalty D-C. Report each program and exposure condition separately before combining them.

An owner identifies the matched schedule/input/seed experimental unit. Shared clean A/C cells are references, not extra independent owners. Split development/selection owners and inputs from independent evaluation before inspecting evaluation results. Keep the candidate and resource conditions fixed for evaluation.

`simulation.analysis.paired` accepts a reusable CSV contract:

```csv
program,candidate,owner,cell,cycles,status
example,P_ECC,eval-001,A,100000,PASS
example,P_ECC,eval-001,B,110000,PASS
example,P_ECC,eval-001,C,102000,PASS
example,P_ECC,eval-001,D,105000,PASS
```

```bash
.venv/bin/python -m simulation.analysis.paired work/trials.csv --seed 548 --bootstrap 10000
```

The analysis resamples complete matched owners, reports B-D and its percentile bootstrap interval, and exposes failed/incomplete owners. It provides no confidence interval from a single owner. Complete-PASS intervals are conditional on those owners and do not erase failures. Check any adaptive selection or multiple-comparison claim separately.

Use a separate input file per exposure/resource condition, or add a `condition` column. When present, this column is part of the grouping key, so SOURCE and WHOLE are never pooled by the analysis.

## Shared experiment artifacts

Prepare scientific producers from a fixed Git commit. Use a fresh output namespace containing that commit, the exact input choice, command, generated schedule, runtime logical-state manifest, stdout/stderr, stats, and validation status. Runtime manifests define injection targets and are necessary experimental outputs; source-file hash inventories and one-off report generators are not project modules.

The source tree contains reusable implementations and gates. Put private benchmark inputs and large outputs in ignored local storage. Keep any shareable result table small, with explicit conditions and a command that can reproduce it. An implementation cleanup or checksum smoke does not produce new scientific CPU results for an earlier experiment matrix.
