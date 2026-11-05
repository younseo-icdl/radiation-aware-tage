# Architecture

## Three layers

`radiation/` produces external logical upset schedules. It validates measured data separately from choices about event arrivals, multiplicity, logical placement, and time compression. It does not inspect predictor outcomes.

`tage/` implements predictor state and protection. The same backend serves standalone replay and gem5. State injection uses explicit logical fields, never host object bytes or `sizeof`. Raw history and folded history are independently writable; injection does not automatically recompute one from the other.

`simulation/` drives the implementation and measures its behavior. Functional replay counts branch prediction errors. gem5 O3 executes a program and measures modeled CPU cycles and IPC. A trace result cannot establish CPU slowdown.

## Predictor and selected state

The backend is based on gem5 v25.1.0.1, commit `c8222cc67a399bfc01e8658dd14b30d5bfd634f9`. The plain TAGE geometry has seven tagged banks, minimum/maximum history lengths 5/130, 16 path bits, and tag widths 9/9/10/10/11/11/12. The update schedule retains conditional training, allocation RNG draws, usefulness aging, and history updates.

The selected protection scope is 23 natural words totaling 346 bits:

| Word indices | Role | Bits |
|---|---|---:|
| 0–20 | Index fold and two tag folds per bank | 200 |
| 21 | Raw direction history, indexed by logical age | 130 |
| 22 | Path history | 16 |

The backend also contains research hooks and inverse history bookkeeping used by the finite source implementation. Zero-fault equivalence tests compare the adapter with direct calls to this shared backend; they do not establish that all faulted behavior equals pristine upstream gem5.

`predictor/tage_adapter.hpp` is the non-speculative replay adapter. `predictor/protected_adapter.hpp` adds immediate functional protection checks. These checks have no CPU timing semantics.

## Protection implementations

| Policy | Action | Known boundary |
|---|---|---|
| P0 | Retain damaged state | No protection |
| P_ED | Detect parity mismatch, exclude tagged prediction/training, refill from real outcomes | Even-bit errors may be undetected |
| P_ECC | Correct single errors with shortened extended Hamming; double-error indication starts refill | Three or more errors can be missed or miscorrected |
| P_TMR | Vote three stored copies and repair disagreements | Correlated errors in two copies can defeat majority voting |

`protection/word.hpp` provides explicit bit vectors, SECDED, and majority voting. `protection/history_controller.hpp` is the functional selected-history controller. The finite implementation uses `pipeline/vector_protection.hpp` and `pipeline/source_protection.hpp`, with registered operands and publication after service. It is not an immediate controller plus a delay charge.

Periodic parity checks every 64 eligible history operations. Exact direct folding computes folds from source history instead of storing recurrent fold state. These are additional comparisons; all four mandatory selected-state baselines remain available.

## Finite CPU resource model

`pipeline/service.hpp` owns authoritative source storage, finite command/read/response/acknowledgment queues, source versions, ID/epoch state, and source-head handling. `pipeline/lookup_port.hpp` adds four token-bound provider contexts. `pipeline/controller.hpp` connects ingress, service, lookup, retirement, and squash handling. `transport/` supplies response payload and mirrored SECDED metadata encoding.

The recurrent source query and source update latencies are separately declared as L=1 or L=2. Exact direct supports query L=1/2 and a fixed source update L=1. Their nominal initiation interval is II=1. A lookup also crosses an actual provider stage. Operand sampling and publication occur in the implemented stage order. Same-source dependencies and ordered publication can reduce achieved throughput even when independent requests reach one per cycle.

The model includes a vector protection check stage, encode/publication staging, and one decoded repair holding slot. The common P0 finite reference traverses matched no-op stages. Consequently, a small or zero protected-minus-P0 clean cycle difference does not imply zero hardware protection cost. Stage fit and port capacity are software assumptions, not measured RTL timing.

O3 changes are limited to the integration under `simulation/gem5/overlay/`: prediction admission/response consumption, actual retirement outcomes, pending ownership, recovery barriers, and squash cancellation. Next-PC/history dependencies remain part of the CPU execution path. A component's independent-request throughput is not the throughput of a real dependent branch stream.

## Fault scope and safety

At initialization the finite gem5 model emits `logical_manifest.json` containing table state, source storage, queues, latches, IDs, epochs, protection metadata, and explicit exclusions. This is a runtime injection interface. It is not a source-file inventory.

The source ring and protocol queues are physical logical storage in the model, including inactive retained history cells that can later reenter. Their faults must not be called harmless merely because they lie outside the currently selected 346 bits.

Detected uncorrectable metadata or illegal ownership fails closed. Such a run is a failure/DUE outcome, not a successful zero-impact injection. Functional safety gates cover stale responses, epoch wrap, FIFO/head state, intermediate stage upsets, and real-outcome refill. They do not prove arbitrary multi-bit tolerance or program correctness for every workload.
