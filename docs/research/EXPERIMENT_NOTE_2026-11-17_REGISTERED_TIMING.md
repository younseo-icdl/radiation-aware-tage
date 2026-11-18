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

## Checkpoint STA at a common period

At the next observation the 6.5 ns primary flows had both passed
clock tree synthesis and entered routing. Lease4096 reached RC
extraction and post-route optimization with an intermediate setup
slack of -0.47 ns. Final reports remained pending.

The timing tool now accepts `--recheck-period-ps` for a fresh
checkpoint session. It retains the extracted network and replaces
the functional MMMC constraints with a private SDC copy whose only
edit is the clock period and waveform. The session records setup,
hold and unrestricted/no-undo query paths. This prepares a
fixed-placement STA recheck if the final common starting target
needs adjustment. It does not reoptimize the layout. Negative
hold or unresolved operand feedback continues to prevent CPU
qualification. Focused parsing and SDC preservation tests passed.
The actual checkpoint recheck depends on completed routed files.

## First routed reports at 6.5 ns

Both primary Innovus flows completed CTS, routing and extraction in
attempt 1. DRC and signal connectivity report no violations or
problems. Final setup and hold still fail at this reference:

| Design | Routed logic area (µm²) | Die utilization | Setup WNS | Hold WNS |
|---|---:|---:|---:|---:|
| Recurrent | 205,950.348 | 82.6245% | -0.814 ns | -0.002 ns |
| Lease4096 | 184,976.856 | 74.2102% | -0.411 ns | -0.006 ns |

The common die area was 249,260.544 µm². The coordinator retains these
results and will use measured areas for the next sizing attempt after
Hybrid05. A fresh diagnostic session is running on the first two
checkpoints at 7.4 ns, rounded upward from 7.314 ns, solely to verify
the common-clock recheck and examine the undo cone. Both old hold
failures still require repair. Future registered flows now request
the +30 ps hold optimization margin used by the local physical
reference. Final report gates still determine actual slack.

Preserved reports: `work/b1a-route-20261117-r6/attempt1/`.
Temporary diagnostic reports: `work/history-checkpoint-diagnostic-20261117-r1/`.

### Checkpoint result and revised route

Both Innovus diagnostic sessions completed at 7.4 ns. The postprocessor
initially rejected the registered hold heading `Hold Check`. It now
accepts that heading as early analysis and continues to verify the fast
view. The existing reports were parsed again without rerunning Cadence.

| First routed checkpoint | Setup WNS | Hold WNS | No-undo query WNS |
|---|---:|---:|---:|
| Recurrent | +0.198 ns | -0.004 ns | +1.093 ns |
| Lease4096 | +0.054 ns | -0.007 ns | +1.376 ns |

The strongest path still includes the common history query boundary.
Constraining undo to zero improves query slack by 0.895 ns and 1.322 ns
respectively. The first lease unrestricted worst query starts on an
undo count bit. Disabling undo leaves a head-register-to-query path.
This identifies a timing opportunity in separating redirect recovery
from normal delivery. Externally supplied prediction and append-to-query
feedback still need their own timing contract.

The revised matched primary batch started under
`work/b1a-route-20261117-r7/` at 7.4 ns, with a common initial die side
of 528.426 µm based on measured cell areas, and a positive 30 ps hold
repair target. Its fresh layout must satisfy actual 65–75% utilization,
DRC/connectivity, setup and hold. The earlier sizing coordinator was
retired to avoid duplicate primary retries. The live Hybrid05 job
was preserved as a separate diagnostic. STA and bounded activity
power watchers now target the revised batch. The power watcher only
runs after the density gate and nonnegative routed timing at the
chosen shared clock.

### First 7.4 ns routing attempt

Both variants completed routing on a common 279,301.672 µm² die.

| Variant | Placed area (µm²) | Die utilization | Setup WNS | Hold WNS | Violating hold paths |
|---|---:|---:|---:|---:|---:|
| Recurrent | 215,870.058 | 77.289% | -0.688 ns | -0.008 ns | 60 |
| Lease4096 | 203,197.248 | 72.752% | -0.471 ns | -0.012 ns | 122 |

Recurrent utilization exceeded the required range. Its limiting setup
path ran from a head register to a query index. The lease limiting setup
path ran from `undo_count_i` to a query tag. The limiting hold endpoint
in each variant was a checkpoint flop reached from its own Q through
combinational feedback. The VCD-derived power and CPU backannotation
gates remain closed. Original routed checkpoints and reports are in
`work/b1a-route-20261117-r7/attempt1/`. A fresh common 547.114 µm die
attempt is running under `attempt2/`.

An isolated setup/hold diagnostic restores the first lease checkpoint
at 8.2 ns, records the restored common-path pessimism removal (CPPR)
setting, compares both-edge CPPR, and attempts incremental hold repair
with the same +30 ps target. This run diagnoses the origin of the
remaining short paths before touching a density-accepted checkpoint.
Its output is `work/history-hold-repair-20261117-r1/`.
