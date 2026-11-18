# Online bank mismatch observation

TAGE has a correctness label when a branch resolves. A history monitor can
observe whether the stored fold of a bank agrees with a simultaneous canonical
fold of its raw window. The latter is an internal consistency label. It can
detect an exposed discrepancy from raw-only or fold-only damage while the
discrepancy survives. A coherent corruption, a change outside the sampled
window or a cancellation can produce no mismatch. A disagreement gives no
direction of correction or prediction-impact label.

The C++ diagnostic probes one bank per supplied coherent quiescent snapshot
using a fixed round-robin order. Each bank tracks a two-bit saturating score.
Positive observations increment and matching observations decrement the score.
The prototype requires no test identity, golden data, injected location or
fault timestamps. On a quiescent boundary the canonical results can share the
lease computation. Every additional probe needs raw access, XOR and compare
logic and scheduling. A realizable implementation would also add at least
14 score bits and a three-bit probe pointer, with corresponding exposure.
Repeated scans seeing the same residual do not count independent events.

The standalone C++ test covers deterministic bank order, saturation, decay,
and unchanged predictor state. It also sweeps all 130 raw sites or all 200
fold sites, starting the same seven-probe round-robin budget at each of its
seven phases. An injected discrepancy persists across the supplied snapshots.
The monitor receives only the current bank's consistency label.

| Condition | Site and phase combinations | Detected on first probe | Detected within seven probes | Latest first detection |
|---|---:|---:|---:|---:|
| Raw bit changed, folds held | 910 | 304 | 910 | 7 |
| Fold bit changed, raw held | 1,400 | 200 | 1,400 | 7 |
| Raw bit changed, folds made consistent with it | 910 | 0 | 0 | None |

The first-probe column is the coverage if an otherwise identical discrepancy
survives only until the next probe. The seven-probe result measures persistent
observability under matched probe budgets. Probe opportunities are supplied by
the test. In O3 they depend on coherent snapshot availability and scheduling,
so the table supplies no CPU-cycle latency or workload fault detection rate.
Repeated observations can raise a score for one sustained discrepancy.
Scores are excluded from the fixed lease. A policy that uses them still needs
a bound on service for every bank and a measurement of its additional cost.
