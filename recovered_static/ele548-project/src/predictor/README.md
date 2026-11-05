# Stage0 predictor adapters

`gshare_adapter.hpp` is new research code. HW1 reference stays read-only under
`sources/prior_hw1`; its allocated UINT32 counters correspond to **2 logical bits**.

`tage_adapter.hpp` wraps the exact pinned `gem5::branch_prediction::TAGEBase`.
It does not replace allocation, alternate-provider, counter update, u aging,
history hashing, or folded-history transitions. `prepare_tage_standalone.py`
retains upstream copyright and only substitutes the statistics constructor;
standalone headers supply simulator plumbing without changing the algorithm.
The checkout must be present at the locked commit. No SC/loop extension exists.

Replay uses one completed branch at a time, actual direction, and the upstream
non-speculative update option. It is not O3 timing or speculative execution.
Snapshots are between branches and own full software buffer/tables/folds/RNG.
No C++ pointers, padding, circular-buffer slack or virtual object state are fault
sites. The six field groups expose 65,370 bits; allocator/aging and CPU bookkeeping
are excluded explicitly in the logical-state manifest.

Raw corruption never rebuilds folded state. Signed 3-bit counters XOR in explicit
two's-complement encoding. An event validates all IDs and duplicates before any
mutation. E2 now declares all actual added parity/check/replica/controller bits
in `sources/e2_protection_logical_manifest.json`. `tage_access.hpp` contains the
logical cell access shared with future CPU integration; the base algorithm is
still compiled directly. `protected_adapter.hpp` and `history_controller.hpp`
implement detector-driven reset/refill, syndrome writeback and vote/repair.

`bash setup/build_e2.sh` runs four-scheme clean/full-state/RNG equivalence,
all stored single-bit cases, SECDED double detection and higher-order limits,
real 130-control refill and snapshot/atomic validation. Fixed E2 holdout results
and rate/population limitations are in `reports/E2_REPORT.ko.md`. This is an
atomic zero-latency non-spec model, not a tested O3 rollback or RTL protocol.

Run `bash setup/run_cpp_stage0.sh` to generate the upstream compilation unit,
compile, and run differential/state tests. Run bounded replay with
`./build/pilot EVENTS_PER_FIELD SEED OUTPUT_CSV` (1..20 events/field).
Source/config/logical manifests and all limits are recorded in the Stage0 report.
