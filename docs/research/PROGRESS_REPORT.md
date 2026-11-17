# Current answers for the professor, 2026-11-17

**Which raw bit changes which fold, when?** A raw-only stored flip at age a<L
after a completed update changes that bank's stored fold on forward append L-a.
Older ages do not enter that bank's forward outgoing route. A production-kernel
sweep over all real banks/widths, raw ages and four input patterns passed.
Direct queries consume changed raw immediately; undo/path/table routes have
different semantics. See `CAUSAL_MICROTEST_REPORT.md` and its measured figure.

**Why do some errors flush while others leave residue?** A coherent wrong incoming
bit contributes to both raw and folds and cancels at window exit. A stored raw
flip changes the value later XORed out without changing what was previously
XORed in; it leaves a rotating fold residual. Raw repair after outgoing consumption
does not erase it. Own-raw rebuilding restores self-consistency, not a golden
source. Persistence is observed to260 updates in this kernel, not infinite CPU
damage or growing Hamming weight. Source-window and raw130 lifetimes differ.

**How are folding and learning separated?** The new microtest has no training.
Existing archived H/F/table interventions and 12 current committed-stream replay
cases remain evidence, not an unexecuted plan. The new package's arithmetic
summary reports 24 historical owners per arm, including H_ONLY/F_ONLY/HF/HFT/FULL;
that is an archived arithmetic recheck, not a new CPU execution. We do not merge
its inputs/horizon with current workloads. Actual BPU direction/target/miss joins
are now available in new CPU traces; full learned-state/RNG recovery is still
not observed. Net-zero misses or retained cycle gap does not prove all damage
stopped.

**What overlaps with prior research?** BADGR addresses TAGE speculative GHR/fold
consistency and implementation cost. ICCD2018/ISPASS2019 evaluate actual L-TAGE
faulted arrays under undervolting, with ISPASS protection caches. PHT graceful
degradation and PVF study other predictor/fault models. Ahead prediction studies
normal timing/energy with missing-history and queue protocols. Our question must
remain stored-SEU propagation and net runtime under explicit matched cost, not
first predictor protection or first periodic consistency. See primary cards.

**Where is normal latency avoided and what is paid instead?** Native remains the
ordinary unprotected path. The quiescent maintenance worker retains recurrent
lookup and pays actual admission stop/drain plus assumed service at publication.
It is not nonblocking. A static bank-select publication kernel now repairs only
selected banks and passes unit gates; it has not replaced a CPU producer. Age,
controller, raw read/align, XOR/write, undo/checkpoint, ports and added exposure
must be measured. A future snapshot worker needs epoch/forwarding/retry and a
defer bound before it can claim overlap.

**What net gain is currently measured?** The completed fixed SOURCE development
batch has 24/24 faulted runs and 3/3 new clean controls, not independent evaluation.
Lease4096's C0/assumed-two-cycle-service qsort benefits are 6.0220% and 12.1057%
for two frozen owners; clean cost is +0.1992%. All detailed program/control losses
and event counts are retained in `../results/source-development-2026-11-17.md`.
These results do not establish a PPA-qualified or population-wide winner. The
earlier forced-event negative study stays separate and complete.

**What remains and which experiment changes a decision?** Finish physical
source/read/update/undo/controller correctness and cost, including actual two
conditional queries/tick, three appends/tick, up to 45 observed undos/tick, and
declared 512-owner capacity. B0 route fails 500 ps for all five designs and has no
activity-energy result. Use the prototype's honest drain cost as comparator
before adding a nonblocking protocol. Backannotate common constraints for native
and candidates; then freeze independent owners/statistics. Do not expand rates,
seeds or candidate families to obtain a win. No further CPU batch is running.
