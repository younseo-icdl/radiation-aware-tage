# Primary-source evidence cards, checked 2026-11-17

The attachment's matrix is prior review evidence, not a claim that those PDFs
were reread here. Checks below distinguish fresh local primary PDFs from primary
text available through the web cache. Local PDFs/extracted text and fetch hashes
remain private in `professor-handoff-20261117-r1/primary-papers/FETCH.json`.
No cached text is assigned a fabricated local PDF hash. This is a focused review,
not an exhaustive novelty or legal assessment. Exact runs from other papers are
not reproduced here.

## TAGE organization: Seznec and Michaud, JILP 2006

[A case for (partially) TAgged GEometric history length branch prediction](https://jilp.org/vol8/v8paper1.pdf).
Fresh primary PDF; Fig.1 on PDF page6 visually checked. It distinguishes the
PC-indexed base from tagged prediction/tag/usefulness entries accessed using
history-derived hashes. This is normal predictor organization, with no radiation
campaign or protection latency claim. It supplies terminology, not proof of the
current gem5 variant. Our exact widths/active loop/SC state come from code/config.
PDF SHA-256: `d103642b0b7297e2771d316485d604b770d748026b25d54e65437121f32d9524`.

## BADGR: Schlais and Lipasti, ICCD 2016

[BADGR: A Practical GHR Implementation for TAGE Branch Predictors](https://pharm.ece.wisc.edu/papers/badgr_iccd16.pdf).
Fresh primary PDF; sections II–V checked, especially PDF pages2–3, Fig.2/3.
Its L-TAGE experiments concern speculative wrong-history and checkpoint/restore,
not particle SEUs. Partial folded-only restoration can desynchronize raw and
folded histories; consistent wrong history can cancel at the outgoing boundary.
The update needs incoming and outgoing history plus rotated previous folds.

BADGR reorganizes history into banks to reduce implementation/checkpoint cost;
it does not remove all recurrence. Its area/power and MPKI comparisons are scoped
to its configurations, not our GPDK45 component. It directly anticipates the
consistency issue, making a claim of first history consistency inappropriate.
Our additional question is delayed stored-raw SEU contamination and net CPU
benefit after matched implementation cost. Comparator need: preserve equivalent
history/rollback semantics and budget actual access/copy ports; reproducing its
full predictor is not necessary for the present causal test.
PDF SHA-256: `575bc85a13ea2bd6a9be3131b7ba540e4c1730f0ba79ac0fb91d4428e4cc85e2`.

## Graceful PHT degradation: Almukhaizim, Verdel and Makris, ICCD 2003

[Cost-Effective Graceful Degradation in Speculative Processor Subsystems: The Branch Prediction Case](https://personal.utdallas.edu/~gxm112130/papers/iccd03a.pdf).
Fresh primary four-page PDF; sections2–4 and Tables1/2 checked. SimpleScalar
gshare/global PHT experiments use SPEC95 and a single-bit error in the most-used
PHT entry. This is not TAGE, GHR folding, or a Poisson storage-upset campaign.
Exact fault persistence remains unspecified in the inspected experimental text.

The encoded counter FSM preserves useful prediction without always reconstructing
the exact original counter; ECC/TMR are compared. The paper treats prediction,
fault detection and update circuitry as implementable in the prediction cycle.
We therefore must permit conventional protection to attempt the same-stage path,
then measure actual timing; an imposed extra cycle is not its inevitable cost.
Its accuracy/logic/storage results do not establish transient folded-history
recovery or our whole CPU energy. Retain it as an architecture-specific graceful
degradation precedent, not a numerical source for our baseline timing.
PDF SHA-256: `4d1caafb2134bfb0918206d1f4fdf518c1c509c7bcefcf2d7f0a66a535a7901e`.

## Permanent-fault performance: Hardy et al., MICRO 2012

[The Performance Vulnerability of Architectural and Non-architectural Arrays to Permanent Faults](https://www.cs.ucy.ac.cy/carch/xi/papers/PVF_micro45.pdf).
Primary cached PDF text checked: section3.1, PDF page2; Table2, PDF page7.
Local download failed certificate validation; local PDF hash unavailable.
The configuration uses gshare, RAS, indirect prediction and cache, not TAGE.
Random permanent stuck-at predictor cells remain in service, while faulty cache
blocks are disabled. PVF/ETV model extra execution-time vulnerability and
population variation; PVF is not interchangeable with raw slowdown.

Transient particle strikes are explicitly outside its model. Our delayed history
residual result examines a different state/mechanism and does not invalidate its
permanent-fault analysis. This paper prevents claiming prior work only studied
correctness. Per-cell permanent-failure probability is not events per second.
A new reproduction campaign would not answer the current raw-tap question.

## L-TAGE undervolting: Chatzidimitriou et al., ICCD 2018

[Analysis and Characterization of Ultra Low Power Branch Predictors](https://www.ceid.upatras.gr/webpages/faculty/gpapad/assets/papers/iccd2018_chatzidimitriou.pdf).
Primary cached text checked: sections III.A–C and IV, TableI, Fig.4. Direct
download returned404; no local PDF hash or fresh visual page claim.
Tournament and L-TAGE are evaluated with gem5/GeFIN, MiBench and modeled power.
The fault maps derive from 14nm undervolted SRAM measurements; long-duration
stuck-at array cells differ from our one-time raw storage XOR.

The paper measures an energy/performance tradeoff and shows that aggressive
voltage reduction can lose energy through runtime penalties. It is genuine prior
TAGE-family fault experimentation. It does not establish our per-bank outgoing
SEU residual or its recovery. Its process, SRAM voltage model, predictor size
and clock assumptions cannot be combined with our educational GPDK45 route
numbers to rank protection. No direct replication is needed for this mechanism
audit; fault-semantic differences must remain explicit.

## BPU protection cache: Chatzidimitriou et al., ISPASS 2019

[Assessing the Effects of Low Voltage in Branch Prediction Units](https://www.ceid.upatras.gr/webpages/faculty/gpapad/assets/papers/ispass2019_chatzidimitriou.pdf).
Primary cached PDF text checked: methodology and sectionV.C–D, PDF page8.
Direct download returned404; PDF hash unavailable. This paper was available in
the prior matrix and is not relabeled an unknown/unobtained publication.
Bi-mode, Tournament, L-TAGE, Perceptron and BTB are examined using gem5/GeFIN
and voltage-dependent permanent SRAM fault maps, with SPEC workloads and modeled
costs. It proposes a locality-based ECC protection cache. At update/retirement,
Branch Repair Table metadata helps detect visible faulty rows; correctable rows
enter the cache and uncorrectable rows are invalidated. Masked stuck-at cells
need not yet be visible.

This is a close protection/cache comparator, not a raw/fold SEU correction proof.
Neither “first predictor protection cache” nor “no prior TAGE fault study” is
defensible. A canonical-fold memo cache would need distinct content/freshness,
added exposure and port cost; table-row ECC results cannot supply those costs.
An exact reproduction is deferred until it changes the selected mechanism.

## Ahead prediction: Cai, Deshmukh and Patt, ISCA 2025

[Enabling Ahead Prediction with Practical Energy Constraints](https://hps.ece.utexas.edu/pub/cai_ahead.pdf), DOI10.1145/3695053.3730998.
Fresh primary PDF; sections4–6, Fig.5 and Table2 checked. This modifies TAGE for
normal prediction timing/energy; it is not radiation protection. Missing
intermediate history motivates secondary tags, a prediction queue and a
single-cycle fallback. Late prediction, queue restart and final selection have
explicit protocols. Normal performance/energy improvements do not transfer to
our CPU, nor supply future actual outcomes to an ahead policy.

For our small known-state preparation study, specify operand availability,
predicted-prefix alternatives, epoch, rollback and queue/latch exposure first.
Moving XOR work earlier without those dependencies does not prove hidden delay.
No full ahead predictor is admitted as a third new integrated family.
PDF SHA-256: `bdb41cbd63b1b32b19e2dd5a0a514841eeafde79c21a95ed570a449d9637f158`.

## Remaining classifications

The prior matrix's AMD periodic TAGE-history consistency patent remains a prior
art lead, not a peer-reviewed SEU experiment or a legal conclusion. Its exact
implementation overlap remains to be checked before a novelty claim. CLEAR
DAC2016 and TCAD2018 are separate versions; this review does not transfer numbers
between them or mark TCAD full text reread. L-TAGE2007 and remaining methodology
sources retain prior evidence status until their primary sections are inspected.
