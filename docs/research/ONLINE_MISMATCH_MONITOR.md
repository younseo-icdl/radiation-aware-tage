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

The unit test covers deterministic bank order, saturation, decay, unchanged
predictor state and a corrupted raw value that agrees with its newly published
fold. The monitor is standalone and does not select a repair or change the
frozen full-bank lease. A later development test can assess the false negative
rate and detection delay at equal probe budget. Any policy using scores must
include a service bound for all banks and pay the added hardware/CPU costs
before separate held-out evaluation.
