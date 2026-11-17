# Actual native TAGE state and propagation boundary

Audit basis: `tage/backend/cpu/pred/tage_base.{hh,cc}`, the native overlay,
`simulation/gem5/configs/{baseline,native_study}.py`, and the retained native
qsort `config.ini` in `work/integrated-clean-20261117-r1/`. The upstream producer
is gem5 v25.1.0.1 pinned at c8222cc67a399bfc01e8658dd14b30d5bfd634f9;
the integrated clean/SOURCE CPU producer is repository commit 1a314be. Later
analysis/microtests do not retroactively change that producer. Full private
binary/input/tape provenance remains with each retained run.

## Tables and history are different state

There is an untagged bimodal T0: 8,192 prediction bits and 2,048 shared hysteresis
bits. `bindex` uses PC only (`instShiftAmt=0`, low 13 bits), not raw or folded
history. Tagged banks each have 512 entries with a 3-bit signed counter, a
bank-specific stored tag and 2 usefulness bits. Their total logical payload is
54,784 bits. A tagged table stores prediction/tag/usefulness, not a compressed
copy of raw direction history. Base selection and learning can still be affected
indirectly by a corrupted tagged provider, despite T0's PC-only index.

The seven direction windows and fold widths appear in `BANK_PARAMETERS.csv`.
There are 63 index-fold bits and 137 tag-fold bits, total 200. S*=346 comprises
these 200, raw130 and speculative path16. It excludes learned tables, raw
retention, checkpoint/control, nonspeculative path and shared target predictors.
The existing whole logical table/history hook covers 65,370 bits, not a complete
physical population or WHOLE exposure certificate.

Bank1 has L=5 with fold widths9/9/8: no history compression occurs. Bank2 has
L=9 and widths9/9/8: the 8-bit auxiliary tag fold compresses while the 9-bit
folds do not. They still use the same incremental class. All banks use path in
`gindex` (min(L,16) bits), while `gtag` uses PC and two direction folds only.
Changing path therefore has an immediate index route without directly changing
direction folds. An immediate raw-only stored upset does not rewrite folds.

This configuration has plain TAGE, not L-TAGE or TAGE-SC-L: no loop predictor
or statistical corrector is instantiated. Shared BPU components do exist:
SimpleBTB4096, RAS16 and SimpleIndirectPredictor256x2. Their target decisions can
override the TAGE direction context, so TAGE direction difference is not the
complete final-BPU miss metric. New native traces export actual BPU observations.

## Actual recurrence and restore

`updatePathAndGlobalHistory` computes path, then calls `updateGHist`. Normal
direction history inserts one predicted direction bit, including unconditional
history callbacks. After raw append, `FoldedHistory::update(h)` reads new h[0]
and outgoing h[L] with the already advanced head. Equivalently it reads old
age L-1. Age zero is youngest; the fault setter writes the used bit of the raw
byte and does not also recalculate folds, codes or path.

For a raw-only event after a completed update at age a<L, the first corrupted
outgoing sample is consumed L-a forward single-bit appends later. For a>=L,
that forward route has no effect on the bank. No training/undo is present in
this theorem. Direct queries instead consume current raw at lookup immediately.

Speculation changes the available routes. `restoreHistState` restores saved
path and algebraically reverses each inserted raw bit using CURRENT live raw,
then advances head. It does not load saved `ci/ct0/ct1` fold arrays. Those arrays
are written by `recordHistState` but not consumed by this pinned restore. The
physical implementation must preserve this behavior for inconsistent/faulted
raw and folds; rebuilding canonical folds during ordinary undo would repair the
baseline silently. 63,000 bulk-inverse comparisons support the proposed algebra,
not a free hardware undo port.

The software raw array has 2,097,152 byte slots carrying one used bit each and
rollover copies maxHist+1000 used slots. This is software retention, not a silicon
SRAM size claim. A replacement physical ring must preserve all live retained
windows and restore behavior. The CPU declares/asserts at most 512 owners;
observed workload peak46 does not permit silently sizing the contract to46.

`STATE_MAP.csv` lists lookup/write/lifetime/injection boundaries. Chooser, aging,
actual learning RNG, owner/head/timer/busy and target-predictor metadata are not
complete WHOLE targets. Raw/source-copy provenance and fold invariant are not
full learned-state recovery. No existing C++ PASS certifies O3 timing or PPA.
