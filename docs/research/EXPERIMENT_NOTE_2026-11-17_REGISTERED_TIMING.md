# Registered history timing and the CPU contract

## Question

Can the recurrent and lease4096 history circuits share a measured clock
under the requested 65–75% die utilization while preserving the existing
prediction and recovery behavior? The mapped 500 ps violations motivate
checking which path sets the admissible clock and whether the CPU can
supply its inputs by the assumed time.

## Physical batch

- Input: fourth Genus batch, common GPDK45 site, frozen RTL 69d8e72 and
  500 ps reference constraints. All three maps wrote a completion marker,
  ended normally and produced validated netlists, constraints and reports.
  The terminal wrapper status was reconstructed from these artifacts,
  with the original stale record retained.
- First route plan: common square die near 499.138 µm per side, two
  concurrent Innovus runs, three CPUs each, identical physical views.
  At the initial observation, recurrent and lease4096 were live in
  placement and Hybrid05 was queued. Raw logs and per-attempt results:
  `work/b1a-route-20261117-r5/`.
- Measured decision gate: use routed die bounding boxes, detailed
  cell area, actual CTS, setup and hold STA, DRC and connectivity.
  Adjust die size from observed cell area if the density misses the window.
  Timing and power remain pending at this observation.

## Implementation and validation

`simulation.eda.history_timing` reads completed registered recurrent
and lease4096 producers. It validates CTS status, density, analysis
direction, corner, units and shared source/clock target. It captures the
first path endpoints and computes an initial common history period from
the largest setup deficit. It retains hold violations separately and
labels the output `SUBSYSTEM_ESTIMATE_ONLY`. The estimate is for deciding
what period to recheck in STA. It carries no CPU timing authorization.

```sh
.venv/bin/python -m simulation.eda.history_timing \
  --recurrent ROUTE/recurrent --lease ROUTE/lease4096 \
  --output FRESH/history_timing.json
```

Focused EDA tests pass for ps conversion, analysis and corner rejection,
and the existing site and density checks. The optional `--audit-no-undo`
restores each routed checkpoint in a fresh Innovus session. It measures
the unrestricted query, then constrains all ten undo count bits to zero
and measures again. The result tests sensitivity to the undo cone while
leaving prefix and other operand arrival assumptions intact. Checkpoint
and reports from the original route are preserved. The command is queued
behind the density pass. Cadence mode results are pending.

## Operand dependency audit

`BPredUnit::predict` obtains a conditional direction, resolves target
availability and then calls `updateHistories` with the final speculative
direction. TAGE's next call can see that append. The RTL supplies two
query lanes with an externally selected append prefix. Its functional
vectors drive both the prefix and the earlier append direction from the
testbench. A routed port-to-port result therefore needs a separate
feedback budget for tagged table lookup, provider and target selection,
and prefix arrival. Peak query counts show demand. They cannot prove
that the dependent operand arrives inside the modeled clock.

The mapped critical path starts at a head register and reaches a query
tag for both primary designs. Compare normal no-undo query paths with
redirect paths in the routed design to identify whether the undo cone
accounts for the slow path. If a stage split is needed, verify its
prediction/update/restore ordering in RTL and gem5 before held-out runs.
For lease, separately check the publication edge and admission control.
Use a shared clock supported by both methods and preserve absolute
SOURCE ticks. The held-out workload and seed lock remains sealed while
physical and causal gates are pending.

## Placement and committed operand check

About 24 minutes into the first physical batch, both primary producers
were still live in pre-CTS placement optimization. The latest observed
GigaOpt WNS snapshots were -5.584 ns for recurrent and -5.188 ns for
lease4096 under the 500 ps reference. Reported optimizer densities were
97.67% and 88.09%. These values describe the optimizer's placement
metric. The requested final metric divides routed cell area by actual
die area, so both remain pending until post-route reports are available.

To measure how often the prefix dependency appears in retained CPU
evidence, scanned the three clean native committed traces. Selected
adjacent conditional records with consecutive increasing lookup IDs
and equal lookup ticks. Compared source epochs, full raw windows and
speculative path values from the pre-append snapshots. Lookup IDs
increased strictly within each conditional stream. The raw limbs were
compared as exact decimal strings in the final aggregate, avoiding the
floating-point conversion risk in the first analysis script.

| Program | Conditional records | Same-tick consecutive conditional pairs | Changed epoch and raw | Changed path |
|---|---:|---:|---:|---:|
| qsort | 6,842,112 | 1,071,903 | 1,071,903 | 958,596 |
| dijkstra | 9,117,873 | 864,052 | 864,052 | 864,019 |
| SHA-1 | 791,758 | 1,328 | 1,328 | 226 |

Evidence and final aggregation script:
`work/b1a-dependent-query-audit-20261117-r2/`. The first fresh attempt
is preserved separately. This is a committed sample and excludes
speculative queries that were later squashed. On every qualifying pair
the second query saw a different raw window, reinforcing the need to
close the prediction-to-append feedback path or explicitly schedule
the dependent query across edges. A two-port count alone cannot justify
a common no-stall CPU clock. No new CPU experiments were run.

## Physical fallback under a feasible optimization target

At the later 50-minute observation both primary runs still spent
time in pre-CTS timing optimization. The last reported optimizer
WNS was -5.383 ns and -5.097 ns for recurrent and lease4096. These
snapshots do not qualify a clock, but they indicate that closing
500 ps in this datapath is an unsuitable optimization target.

The route launcher accepts an optional registered history clock
period in its private site file. It changes only the generated
history clock and half-period waveform in a fresh copy of the SDC.
The original netlist and constraints are retained. The timing
summary uses the route's period for its estimate.

A fallback at a common 6.5 ns optimization target is queued only if
the original route coordinator becomes terminal without a density
pass. The value is a provisional target chosen above the latest
pre-CTS estimate, rather than a measured CPU clock. The attempt
will reuse the same mapped designs, PVT, floorplan sizing procedure
and the 65–75% die utilization requirement. Reports and producer
status are kept in a fresh batch. Profile timing in the routed
design will determine what can be backannotated.

The first primary pair became terminal before Hybrid05. Recurrent
ended with timeout status 124. Lease4096 ended with status -9 and
worker assertions in the partial log. The process termination
mechanism beyond that status is unverified. Neither produced a
completed routed timing package. Hybrid05 was still live. The
primary failures made the original batch ineligible, so the idle
fallback watcher was retired and the revised batch launched
without waiting for the remaining Hybrid05 job.

The fresh `work/b1a-route-20261117-r6/` logs and producer records
show recurrent and lease4096 started with the intended 6.5 ns
clock and 3.25 ns half-period. The older Hybrid05 run was preserved.
The revised batch has its own terminal density watcher for the
matched timing and no-undo path analysis. The physical result is
pending. The online observer producer and the directed publication
phase check are documented in the separate history activity note.
