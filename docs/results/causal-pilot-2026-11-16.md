# Focused causal pilot

Twelve predetermined committed-replay cases completed with seed 548, injection
before branch 2049, and observation through branch 8192. Each of SHORT-INT-1 and
SHORT-FP-1 used R0, R64, path bit 0, shortest index-fold bit 0, longest second-tag
fold bit 0, and atomic R0;R1. These are mechanism controls, not independent
radiation samples. All full-state sanity checks passed, and the joint-restoration
arm reproduced the shadow prediction stream in all twelve cases.

At the first post-source aligned boundary, Y00 retains both faulty folds and
learning state, Y10 restores only folds, Y01 only learning state, and Y11 both.
Learning restoration includes chooser, aging, and allocation RNG state. Values
below are signed net extra suffix misses relative to the shadow; negative values
are helpful. They are **not CPU cycle estimates**.

| Trace | Site | Boundary | Y00 | Y10 | Y01 | Y11 |
|---|---|---:|---:|---:|---:|---:|---:|
| INT | R0 | 2179 | 214 | 0 | 213 | 0 |
| INT | R64 | 2115 | 2 | 0 | 2 | 0 |
| INT | path0 | 2065 | 1 | 1 | 0 | 0 |
| INT | index-short | 2049 | 19 | 0 | 19 | 0 |
| INT | tag1-long | 2049 | 0 | 0 | 0 | 0 |
| INT | R0;R1 | 2179 | 213 | 0 | 210 | 0 |
| FP | R0 | 2179 | 273 | 2 | 271 | 0 |
| FP | R64 | 2115 | -3 | 0 | -3 | 0 |
| FP | path0 | 2065 | -2 | -2 | 0 | 0 |
| FP | index-short | 2049 | 6 | 0 | 6 | 0 |
| FP | tag1-long | 2049 | 0 | 0 | 0 | 0 |
| FP | R0;R1 | 2179 | 267 | 2 | 269 | 0 |

Fold restoration does not imply prediction-stream recovery. INT R0's Y10 net
zero consists of seven harmful and seven helpful predictions; FP R0's Y10 has
eight harmful and six helpful predictions. The path cases retain a learning
effect that fold restoration cannot remove. Interaction is nonadditive in the
raw-pair cases (signed interaction +3 INT and -4 FP). Helpful and zero effects
are retained rather than filtered out.

Raw/fold cases still have reference-fold differences at the observation horizon;
their stable fold recovery is right-censored. Path cases never affected folds.
Source disappearance here means semantic active history in quiescent replay,
not physical-cell overwrite or disappearance from speculative CPU checkpoints.
There is no timing recovery observation and no fixed miss-penalty conversion.

Private artifacts: `work/causal-pilot-20261116-r1/CAUSAL_PILOT_PLAN.json`,
`PILOT_RESULTS.json`, and each case's state, query, suffix-arm, interaction, and
recovery timeline files. Historical experiments remain accepted as reported;
this pilot answers the additional intervention question and does not authenticate
or reproduce historical batches.

The next decision requires native unprotected CPU fault effects and actual
retirement times. A minimal native injector and read-only trace are being added
for that purpose. Its implementation regression must pass before workload use.
Only then can a candidate's necessary modeled cost be compared with matched UF;
this replay alone establishes neither speedup nor physical hardware cost.
