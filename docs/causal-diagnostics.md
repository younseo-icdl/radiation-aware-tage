# Causal recovery diagnostics

These tools address a missing causal question rather than reproduce the historical propagation/CPU campaigns: after semantic source recovery, how much of the remaining prediction damage is removable by folds, learned state, or their interaction?

## Contract

`tage-causal` uses a fixed committed branch stream. Every arm generates its own lookup/provider/training metadata, consumes actual outcomes, and follows the unchanged plain TAGE training/RNG order. Speculation is removed. There are no pending requests or restorable checkpoints at intervention boundaries. This is **COMMITTED_ONLY_REPLAY**, not a native CPU execution or a physical fault-rate experiment.

One atomic event is applied before a declared branch lookup. `R<age>` resolves against current active raw history once at injection; `W<word>:<bit>` selects an explicit selected-history word. Semicolon-separated distinct sites form one XOR event. Invalid/duplicate groups are rejected before any write or output-directory creation. Neither injector nor observer rebuilds folds or repairs check bits automatically.

The timeline measures active raw/path, non-speculative path, head, each index/tag fold's invariant/reference distances, learned fields, RNG equality, queried indices/tags/providers, and harmful/helpful predictions. Bit counts and learned-field counts are different units. A disappearing semantic raw difference is not a measured physical-cell overwrite; overwrite time is explicitly unknown.

Four detached queries use the same pre-lookup context:

| Query | Source/folds | Learned state |
|---|---|---|
| Q0 | Current H/F | Current L |
| QF | Current H, Phi(current H) | Current L |
| QH | Shadow H, Phi(shadow H) | Current L |
| QL | Current H/F | Shadow L including chooser/allocation clock/RNG |

Queries act on detached model copies and do not change the live model or RNG. The current implementation supports the ordinary all-bank replay contract; masked/fallback admission is rejected rather than silently cloned incorrectly. Query effects are immediate diagnostics, not future-feedback contribution percentages.

At the first observed quiescent boundary with matching semantic raw/path/non-speculative path and head, four copies of the same faulty snapshot are continued over the identical suffix:

| Arm | One-time intervention |
|---|---|
| Y00 | None |
| Y10 | Restore folds |
| Y01 | Restore learned tables, chooser/allocation clock and RNG |
| Y11 | Both |

No additional fault or periodic gold copy is applied. A separate full-state sanity copy must match the shadow's predictions, complete stored state and RNG. Y11 prediction equality is checked separately. Learned-state repair includes bimodal prediction/hysteresis, tagged counters/tags/usefulness, aging, chooser and RNG. It does not pretend to restore absent CPU pending/control state.

The outcome is signed net extra misses over the suffix: harmful minus helpful. Report Y00-Y10, Y00-Y01, Y00-Y11 and interaction `Y00-Y10-Y01+Y11`. A zero net count can contain nonzero harmful/helpful events and is not prediction-stream recovery. Do not convert these counts into CPU cycles with a fixed penalty.

## Commands and outputs

```bash
make build/tage-causal CXX=/path/to/g++
build/tage-causal --trace /private/branches.txt \
  --trace-format pc-target-taken-conditional --site R0 \
  --event-branch 2049 --limit 8192 --output work/causal-new
.venv/bin/python -m simulation.analysis.recovery work/causal-new \
  --output work/causal-new-analysis
```

The default trace format is `pc taken target conditional`, matching the functional replay interface. The transferred SHORT-INT/SHORT-FP files use `pc target taken conditional`; choose that format explicitly. Output directories must be fresh.

Outputs include `case.json`, `STATE_AND_EXPOSURE_MANIFEST.csv`, `STATE_DISTANCE_TIMESERIES.csv`, `CAUSAL_LOOKUP_QUERIES.csv`, `CAUSAL_SUFFIX_ARMS.csv`, and `CAUSAL_INTERACTIONS.csv`. The recovery reader writes state/access/prediction summaries in `RECOVERY_TIMELINE.csv`, retaining first zero, last nonzero, observed stable suffix, recurrence, and censoring. Callback, branch, history-update and conditional-history coordinates remain distinct.

`RECOVERY_WINDOWS.csv` is explicitly NOT_APPLICABLE for replay without CPU time. The separate `timing_windows` API accepts aligned exact paired CPU checkpoints, checks finer subwindows for cancellation, distinguishes last positive from last nonzero aggregate excess, and permits a retained cumulative time offset. Default windows are 1024 conditional branches, three complete windows, epsilon zero. Coarse endpoints, missing boundaries, late observation, and alignment gaps do not become fabricated recovery times.

## Initial decision-focused pilot

Use the two transferred SHORT-INT/SHORT-FP traces as mechanism controls, not substitutes for the three MiBench CPU workloads. Predeclare six cases per trace: R0, R64, path bit W22:0, first index fold W0:0, longest-bank second tag fold W20:0, and atomic R0;R1. Use predictor seed 548, event branch 2049, and observation through branch 8192. There are twelve fixed diagnostic cases, not twelve independent radiation owners or population samples. No tuning to the measured winner and no holdout claim is involved.

The pilot's decision is whether fold-only restoration leaves consequential learned-state effects and cancellation, and whether a bounded rebuild or a learning/control intervention deserves a small CPU test. Native fault/runtime comparison remains a separate required measurement before claiming the user's primary objective.
