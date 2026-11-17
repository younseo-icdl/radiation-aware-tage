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
