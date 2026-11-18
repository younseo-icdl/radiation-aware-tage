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

**What does the matched layout establish?** The registered history blocks
completed routing at 72.11% and 68.46% die utilization on the same GPDK45 die.
They passed an 8.100 ns postroute recheck with setup/hold slack of +179/+74 ps
for recurrent and +10/+68 ps for lease. Clock, raw ring, path checkpoints,
folds and the lease controller are in scope. The lease layout used 5.06%
less placed cell area. The full 80,001-edge clean checksum replay directly
annotated all routed nets and flop outputs at the same clock, including five
lease publications. The zero-delay switching estimate was 4.438 versus
3.920 mW, or 11.68% less history-window energy. Gate-delay glitches and
whole-task energy remain outside this measurement. See
`EXPERIMENT_NOTE_2026-11-17_REGISTERED_TIMING.md`.

**What remains and which experiment changes a decision?** Match the
predictor-row, direction, speculative append and restore-owner timing boundaries
before backannotating a common frequency and issue schedule. The qsort replay
shows substantial same-tick query–append ordering. A common conditional issue
interval is implemented and checksum-tested. An issued prediction still needs
to reach the same-edge history append, and its path has a measured external
deadline around 4.7–4.8 ns at the current 8.1 ns block clock. The held-out
Basicmath, Patricia and CRC32 set is locked. Its 54 runs begin after the
timed CPU contract and bounded checks pass. See the provider note and
`HELDOUT_LEASE4096_LOCK.md`.

**What changed in the staged implementation?** Registered hash capture and
subsequent row return now have separate CPU edges with cancellation and
matched single-conditional-training-port control. The actual CPU row,
target and owner captures reproduce the RTL's staged operands on 80,001
edges per arm. The scan-free staged layouts routed at 72.98% and 72.63%
die utilization. Extracted tagged and T0 read references take 5.074 and
5.637 ns. With the derived late data and stated target-valid deadline,
the staged layouts and bounded gem5 gate pass at 13.850 ns. At this
clock and using actual CPU rows, the routed history estimates are
2.389 versus 2.517 µJ, a 5.38% increase for lease. Scope is the clean
history-block window, with all nets directly annotated and zero cell
delay. The separate target-validity path is being characterized before
the held-out evaluation opens. See
`EXPERIMENT_NOTE_2026-11-17_STAGED_QUERY.md`.
