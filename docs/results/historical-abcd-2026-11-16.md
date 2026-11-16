# Historical R2 and B4 CPU reanalysis (2026-11-16)

This analysis answers the historical part of the three-question evaluation using completed CPU records. It launches **zero new gem5 runs**. It uses an isolated checkout and output directory; the separate sonnet chat continues causal/recovery and native-fault implementation. No producer, build, workload input, event schedule, or running output is changed.

## Evidence and reuse

| Evidence | Completed scope | Reuse here | Boundary |
|---|---|---|---|
| R2 `CLEAN_RESULTS.csv`, `CPU_ABCD.csv` supplied by the user | 18 clean + 144 fault = 162 PASS; 2 owners/program/condition | Clean cycles/instructions/MPKI; all owner A/B/C/D and MPKI differences | Inline C0 stage-fit model; not newly certified pristine native |
| R2 final report text, handoff `S02_native_r2_162.txt` | Reports the completed 162 runs | Timing, exposure, recovery and interpretation contract | Reported historical evidence; not a replacement for owner data |
| B4 `DEV_CLEAN.csv`, `DEV_ABCD.csv` | 18 clean + 102 fault | Separate development output | 2 owners; never pooled with EVAL |
| B4 `EVAL_CLEAN.csv`, `EVAL_ABCD.csv` | 18 clean + 408 fault | Separate evaluation output | 8 owners/program/condition; baseline is finite P0 |
| B4 `B4_ALL546_CLOSED_RECORDS.json` | 546 program/protocol PASS records | Cross-checks every DEV/EVAL A/B/C/D against recorded execution cycles | Contains commands, identities, instructions, exit and drain counters; does not contain full branch statistics |
| B4 completed report and native system/config gate | Native clean cycles and 18 configuration comparisons | Normal finite-versus-native overhead | Native matched-fault B absent |
| v11 plan, handoff `S07_v11_previous_instructions.txt` | Experimental plan | Defines native baseline and timing requirements | Plans and old caps are not completed measurements or new run admission |
| Current 21-cell clean comparison | Separate completed native/finite cohort | Context only; see [clean report](rhel8-clean-2026-11-16.md) | Different transferred inputs; cannot serve as A/C for historical fault rows |

The original R2 ZIP and full per-run producer artifacts were not recovered here; the two user-supplied CSVs now provide the requested owner-level numerical evidence. Their 162 MPKI rows were independently checked against exported committed mispredictions/instructions (324 checks). All 144 cycle decompositions match the exported increments and net gains. All 510 B4 fault table rows match the corresponding clean/fault closed records in all four cells.

B4 full workload `stats.txt` files were sought in transferred history, raw-record output paths, and available attachments. The local transfer contains checksum and current clean-cohort stats, but no historical B4 workload stats; original recorded output paths are unavailable locally. Therefore historical B4 conditional/all-branch MPKI remains **UNKNOWN**, not zero. Its absence did not trigger new CPU runs.

## Pairing and statistics

A/B are unprotected clean/fault; C/D are candidate clean/fault. Each row preserves `B-D = (B-A) - (C-A) - (D-C)`. R2 U and B4 P0 are explicitly distinct timing contracts. Comparisons never cross program, condition, input cohort, or owner. Shared clean A/C and six method replays are not extra independent observations.

Tables report arithmetic owner means and observed [minimum, maximum]. These ranges are not confidence intervals. R2 n=2 is a pilot; zero loss is not evidence of safety or equivalence. Helpful faults, negative gains, zero loss, original event/censoring columns, and invalid/failure statuses are retained in the analysis outputs. These supplied R2/B4 tables contain no invalid pairs; historical failures outside these completed tables remain in their original records.

## R2 clean controls

All six policies have identical clean cycles, instructions, conditional and all-branch MPKI for each program; every C-A is zero **under C0 stage fit**.

| Program | A = C cycles | Committed instructions | IPC | Conditional MPKI | All-branch MPKI |
|---|---:|---:|---:|---:|---:|
| qsort_small | 5,240,626 | 4,256,767 | 0.812263 | 8.327682 | 8.371847 |
| dijkstra_small | 14,780,359 | 15,515,332 | 1.049726 | 3.521484 | 3.66676 |
| sha1 | 2,478,327 | 4,884,827 | 1.971018 | 0.069808 | 0.094579 |

At the reported 2 GHz clock, one cycle is 0.5 ns. Cycle differences below therefore also determine the modeled execution-time differences; host runtime is a separate quantity.

## R2 unprotected fault damage

| Program | Condition | B cycles, mean [range] | B-A cycles, mean [range] | Conditional B MPKI | Conditional B-A MPKI, mean [range] | All-branch B MPKI | All-branch B-A MPKI, mean [range] |
|---|---|---:|---:|---:|---:|---:|---:|
| dijkstra_small | atomic K2 | 14,822,849.5 [14,821,881, 14,823,818] | 42,490.5 [41,522, 43,459] | 3.627444 | 0.10596 [0.104026, 0.107893] | 3.77272 | 0.10596 [0.103962, 0.107958] |
| dijkstra_small | SOURCE | 15,009,672.5 [14,984,215, 15,035,130] | 229,313.5 [203,856, 254,771] | 4.351083 | 0.829599 [0.717935, 0.941262] | 4.496617 | 0.829857 [0.718386, 0.941327] |
| dijkstra_small | WHOLE x1e15 | 14,773,691 [14,773,030, 14,774,352] | -6,668 [-7,329, -6,007] | 3.529895 | 0.008411 [0.002707, 0.014115] | 3.67559 | 0.00883 [0.002771, 0.014888] |
| dijkstra_small | WHOLE x1e16 | 14,774,215 [14,759,146, 14,789,284] | -6,144 [-21,213, 8,925] | 3.532699 | 0.011215 [0.001805, 0.020625] | 3.678297 | 0.011537 [0.001934, 0.02114] |
| qsort_small | atomic K2 | 5,391,949.5 [5,247,158, 5,536,741] | 151,323.5 [6,532, 296,115] | 12.321558 | 3.993876 [0.012451, 7.975301] | 12.365723 | 3.993876 [0.012451, 7.975301] |
| qsort_small | SOURCE | 5,247,407.5 [5,240,615, 5,254,200] | 6,781.5 [-11, 13,574] | 8.397335 | 0.069654 [0.011276, 0.128031] | 8.4415 | 0.069654 [0.011276, 0.128031] |
| qsort_small | WHOLE x1e15 | 5,242,554.5 [5,240,626, 5,244,483] | 1,928.5 [0, 3,857] | 8.332028 | 0.004346 [-0.00047, 0.009162] | 8.376193 | 0.004346 [-0.00047, 0.009162] |
| qsort_small | WHOLE x1e16 | 5,235,899.5 [5,235,207, 5,236,592] | -4,726.5 [-5,419, -4,034] | 8.326507 | -0.001175 [-0.009162, 0.006813] | 8.370672 | -0.001175 [-0.009162, 0.006813] |
| sha1 | atomic K2 | 2,478,327 [2,478,327, 2,478,327] | 0 [0, 0] | 0.070013 | 0.000205 [0, 0.000409] | 0.094783 | 0.000205 [0, 0.000409] |
| sha1 | SOURCE | 2,489,572.5 [2,478,338, 2,500,807] | 11,245.5 [11, 22,480] | 0.45887 | 0.389062 [0.001842, 0.776281] | 0.483743 | 0.389164 [0.001842, 0.776486] |
| sha1 | WHOLE x1e15 | 2,478,327 [2,478,327, 2,478,327] | 0 [0, 0] | 0.069808 | 0 [0, 0] | 0.094579 | 0 [0, 0] |
| sha1 | WHOLE x1e16 | 2,478,327 [2,478,327, 2,478,327] | 0 [0, 0] | 0.06991 | 0.000102 [0, 0.000205] | 0.094681 | 0.000102 [0, 0.000205] |

SOURCE has a time-based Poisson law of 2000 events/s with atomic K1/K2 marks (205/214 and 9/214), logical raw130 placement, 500 ticks/cycle, and first-exit censoring. The six unprotected owner tapes applied 36 K1 and no K2 events; future events remain recorded. Method replays do not create new independent events. A slower execution may apply more events; event counts are not equalized.

Atomic K2 is one forced event flipping two contiguous logical raw-history ages in the same parity word. Logical adjacency does not establish physical MCU adjacency or a measured MCU rate. WHOLE x1e15/x1e16 uses the reported per-bit stress law and method-specific augmented storage/absent-site handling; it must not be pooled with SOURCE or interpreted as mission FIT.

## R2 protection decomposition

Here A and C are the clean controls above. Full A/B/C/D values and both MPKI decompositions for every owner and policy are in the JSON and sample CSV outputs. Every row below has n=2 and C-A=0 cycles.

| Program | Condition | Candidate | B-A mean cycles | C-A cycles | D-C mean cycles | B-D cycles, mean [range] | B-D as % of A |
|---|---|---|---:|---:|---:|---:|---:|
| dijkstra_small | atomic K2 | Direct | 42,490.5 | 0 | 1,409.5 | 41,081 [38,703, 43,459] | 0.277943 |
| dijkstra_small | atomic K2 | ECC | 42,490.5 | 0 | -2,199.5 | 44,690 [43,459, 45,921] | 0.302361 |
| dijkstra_small | atomic K2 | frequent parity | 42,490.5 | 0 | 42,490.5 | 0 [0, 0] | 0 |
| dijkstra_small | atomic K2 | periodic parity | 42,490.5 | 0 | 42,490.5 | 0 [0, 0] | 0 |
| dijkstra_small | atomic K2 | TMR | 42,490.5 | 0 | 0 | 42,490.5 [41,522, 43,459] | 0.287479 |
| dijkstra_small | SOURCE | Direct | 229,313.5 | 0 | -4,098.5 | 233,412 [203,856, 262,968] | 1.579204 |
| dijkstra_small | SOURCE | ECC | 229,313.5 | 0 | 0 | 229,313.5 [203,856, 254,771] | 1.551474 |
| dijkstra_small | SOURCE | frequent parity | 229,313.5 | 0 | -6,786 | 236,099.5 [210,194, 262,005] | 1.597387 |
| dijkstra_small | SOURCE | periodic parity | 229,313.5 | 0 | -6,972.5 | 236,286 [210,194, 262,378] | 1.598649 |
| dijkstra_small | SOURCE | TMR | 229,313.5 | 0 | 0 | 229,313.5 [203,856, 254,771] | 1.551474 |
| dijkstra_small | WHOLE x1e15 | Direct | -6,668 | 0 | -3,664.5 | -3,003.5 [-6,007, 0] | -0.020321 |
| dijkstra_small | WHOLE x1e15 | ECC | -6,668 | 0 | -3,664.5 | -3,003.5 [-6,007, 0] | -0.020321 |
| dijkstra_small | WHOLE x1e15 | frequent parity | -6,668 | 0 | -3,664.5 | -3,003.5 [-6,007, 0] | -0.020321 |
| dijkstra_small | WHOLE x1e15 | periodic parity | -6,668 | 0 | -3,664.5 | -3,003.5 [-6,007, 0] | -0.020321 |
| dijkstra_small | WHOLE x1e15 | TMR | -6,668 | 0 | -3,664.5 | -3,003.5 [-6,007, 0] | -0.020321 |
| dijkstra_small | WHOLE x1e16 | Direct | -6,144 | 0 | -9,180.5 | 3,036.5 [0, 6,073] | 0.020544 |
| dijkstra_small | WHOLE x1e16 | ECC | -6,144 | 0 | -9,180.5 | 3,036.5 [0, 6,073] | 0.020544 |
| dijkstra_small | WHOLE x1e16 | frequent parity | -6,144 | 0 | -9,180.5 | 3,036.5 [0, 6,073] | 0.020544 |
| dijkstra_small | WHOLE x1e16 | periodic parity | -6,144 | 0 | -9,180.5 | 3,036.5 [0, 6,073] | 0.020544 |
| dijkstra_small | WHOLE x1e16 | TMR | -6,144 | 0 | -9,180.5 | 3,036.5 [0, 6,073] | 0.020544 |
| qsort_small | atomic K2 | Direct | 151,323.5 | 0 | 0 | 151,323.5 [6,532, 296,115] | 2.887508 |
| qsort_small | atomic K2 | ECC | 151,323.5 | 0 | 1,331 | 149,992.5 [3,870, 296,115] | 2.86211 |
| qsort_small | atomic K2 | frequent parity | 151,323.5 | 0 | 151,323.5 | 0 [0, 0] | 0 |
| qsort_small | atomic K2 | periodic parity | 151,323.5 | 0 | 151,323.5 | 0 [0, 0] | 0 |
| qsort_small | atomic K2 | TMR | 151,323.5 | 0 | 0 | 151,323.5 [6,532, 296,115] | 2.887508 |
| qsort_small | SOURCE | Direct | 6,781.5 | 0 | -110.5 | 6,892 [-11, 13,795] | 0.131511 |
| qsort_small | SOURCE | ECC | 6,781.5 | 0 | 0 | 6,781.5 [-11, 13,574] | 0.129402 |
| qsort_small | SOURCE | frequent parity | 6,781.5 | 0 | -1,428 | 8,209.5 [-936, 17,355] | 0.156651 |
| qsort_small | SOURCE | periodic parity | 6,781.5 | 0 | 218.5 | 6,563 [-260, 13,386] | 0.125233 |
| qsort_small | SOURCE | TMR | 6,781.5 | 0 | 0 | 6,781.5 [-11, 13,574] | 0.129402 |
| qsort_small | WHOLE x1e15 | Direct | 1,928.5 | 0 | 1,928.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e15 | ECC | 1,928.5 | 0 | 1,928.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e15 | frequent parity | 1,928.5 | 0 | 1,928.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e15 | periodic parity | 1,928.5 | 0 | 1,928.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e15 | TMR | 1,928.5 | 0 | 1,928.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e16 | Direct | -4,726.5 | 0 | -4,726.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e16 | ECC | -4,726.5 | 0 | -4,726.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e16 | frequent parity | -4,726.5 | 0 | -4,726.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e16 | periodic parity | -4,726.5 | 0 | -4,726.5 | 0 [0, 0] | 0 |
| qsort_small | WHOLE x1e16 | TMR | -4,726.5 | 0 | -4,726.5 | 0 [0, 0] | 0 |
| sha1 | atomic K2 | Direct | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | atomic K2 | ECC | 0 | 0 | 105 | -105 [-105, -105] | -0.004237 |
| sha1 | atomic K2 | frequent parity | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | atomic K2 | periodic parity | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | atomic K2 | TMR | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | SOURCE | Direct | 11,245.5 | 0 | 0 | 11,245.5 [11, 22,480] | 0.453754 |
| sha1 | SOURCE | ECC | 11,245.5 | 0 | 0 | 11,245.5 [11, 22,480] | 0.453754 |
| sha1 | SOURCE | frequent parity | 11,245.5 | 0 | 154.5 | 11,091 [-94, 22,276] | 0.44752 |
| sha1 | SOURCE | periodic parity | 11,245.5 | 0 | 154.5 | 11,091 [-94, 22,276] | 0.44752 |
| sha1 | SOURCE | TMR | 11,245.5 | 0 | 0 | 11,245.5 [11, 22,480] | 0.453754 |
| sha1 | WHOLE x1e15 | Direct | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e15 | ECC | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e15 | frequent parity | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e15 | periodic parity | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e15 | TMR | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e16 | Direct | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e16 | ECC | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e16 | frequent parity | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e16 | periodic parity | 0 | 0 | 0 | 0 [0, 0] | 0 |
| sha1 | WHOLE x1e16 | TMR | 0 | 0 | 0.5 | -0.5 [-1, 0] | -0.00002 |

Direct and TMR remove the qsort K2 cycle penalty in both owners, but the unprotected penalty ranges from 6,532 to 296,115 cycles. For dijkstra K2, Direct retains 1,409.5 mean cycles (one owner: 2,819); TMR retains zero. SHA-1 has zero unprotected K2 cycle penalty, while ECC adds 105 cycles in each owner. Its exported conditional MPKI can change even when cycles do not. dijkstra WHOLE can also show more misses and fewer cycles. Do not convert MPKI into cycles with a fixed miss penalty.

Direct does not dominate SOURCE: frequent parity has larger mean net gain for qsort, periodic parity for dijkstra, and Direct/ECC/TMR tie for SHA-1 cycles. ECC helpful K2 observations and parity negative residuals reflect the complete execution including prediction/training/relearning; they are not isolated repair latency measurements.

## B4: finite P0, not native

The historical completed report gives the following same-cohort clean comparison. All six finite candidates share the same clean cycles. Thus their C-A is zero when A is finite P0, while their normal cost versus native is substantial.

| Program | Reported native clean cycles | Finite clean cycles | Finite minus native cycles | Increase over native |
|---|---:|---:|---:|---:|
| dijkstra_small | 14,781,006 | 23,119,103 | 8,338,097 | 56.410890% |
| qsort_small | 5,433,904 | 12,148,177 | 6,714,273 | 123.562599% |
| sha1 | 2,510,384 | 2,941,798 | 431,414 | 17.185180% |

For SOURCE EVAL (n=8), the reconstructed finite comparison is:

| Program | Candidate | B-A mean cycles | C-A cycles | D-C mean cycles | B-D cycles, mean [range] |
|---|---|---:|---:|---:|---:|
| dijkstra_small | EXACT_DIRECT | 238,953.875 | 0 | -308 | 239,261.875 [122,586, 399,357] |
| dijkstra_small | P_ECC | 238,953.875 | 0 | -37.875 | 238,991.75 [122,155, 398,959] |
| dijkstra_small | P_ED_FREQUENT | 238,953.875 | 0 | 4,316 | 234,637.875 [127,124, 399,354] |
| dijkstra_small | P_ED_PERIODIC_N1 | 238,953.875 | 0 | 6,116 | 232,837.875 [120,442, 393,495] |
| dijkstra_small | P_TMR | 238,953.875 | 0 | 0 | 238,953.875 [122,155, 398,959] |
| qsort_small | EXACT_DIRECT | 426,571.125 | 0 | -2,181.5 | 428,752.625 [32,364, 829,635] |
| qsort_small | P_ECC | 426,571.125 | 0 | -395.875 | 426,967 [31,678, 823,368] |
| qsort_small | P_ED_FREQUENT | 426,571.125 | 0 | -5,417.875 | 431,989 [32,113, 827,176] |
| qsort_small | P_ED_PERIODIC_N1 | 426,571.125 | 0 | -4,567.375 | 431,138.5 [33,758, 821,478] |
| qsort_small | P_TMR | 426,571.125 | 0 | 0 | 426,571.125 [31,678, 823,368] |
| sha1 | EXACT_DIRECT | 12,020.25 | 0 | 421.625 | 11,598.625 [0, 34,577] |
| sha1 | P_ECC | 12,020.25 | 0 | 13.5 | 12,006.75 [0, 37,963] |
| sha1 | P_ED_FREQUENT | 12,020.25 | 0 | 2,574.375 | 9,445.875 [-51, 34,462] |
| sha1 | P_ED_PERIODIC_N1 | 12,020.25 | 0 | 2,614.875 | 9,405.375 [-94, 34,404] |
| sha1 | P_TMR | 12,020.25 | 0 | 0 | 12,020.25 [0, 37,963] |

SBU and WHOLE owner results are included in `B4_EVAL.json` / `B4_EVAL_SAMPLES.csv` / `B4_EVAL_SUMMARY.csv`; DEV is exported separately. Direct has no SSTAR346 stored-fold SBU rows: those comparisons are N/A, not successful zero-damage trials. The B4 supplied matrix has no forced atomic-K2 cohort.

Native fault time was not measured in B4. Substituting native clean A into finite B/D is not a native A/B/C/D experiment. For illustration only, the lowest mean SOURCE D among these five finite candidates would require native fault slowdowns exceeding 56.4088% (dijkstra), 123.4629% (qsort), or 17.1852% (SHA-1) to break even. These are arithmetic thresholds against reported native clean time, **not measured native fault losses**. Exposure duration also differs under a time-based law.

## Timing and resource assumptions

| Contract | Lookup/service and overlap | Checks, writes, dependencies and stalls | Validation boundary |
|---|---|---|---|
| R2 inline C0/U0 | Reported L0/II0 legacy inline path; no finite lookup-port/journal arbitration | Normal check/encode/vote/update assumed to fit existing stages for all methods; modeled repair 4 cycles and common pending correction minimum 1 cycle | Completed historical CPU comparison under this assumption; no full-stage circuit timing |
| B4 fixed finite L1 | Query L1, source update L1, provider/table stage L1, nominal independent II1; provider contexts 4; command/read/response/ingress queues 4; repair hold 1 | Shared 23-lane check/encode; finite P0 follows no-op stages too; source ordering, next-PC/history, retirement and rollback dependencies; queue-full admission stalls; correction/reset barriers can hold progress | Completed CPU/protocol model, not physical stage fit. Observed EVAL max lookup pending 4; max source pending 8/9/8 for qsort/dijkstra/SHA-1 |
| Direct versus incumbent with an additional stage | A new latency/II/readiness/backpressure contract is required | Must charge actual needed source/read/fold/update/checkpoint/restore/control work equally and use CPU timing, not branch-count postprocessing | NOT MEASURED here; do not infer from R2 C0 or B4 shared P0 |

Overlapping stall counts do not form an exact CPI decomposition. D-C includes residual prediction damage and recovery/queue/refill costs together. Extra stage-fit cycles zero does not imply zero area, delay, or energy. No new RTL, Cadence, SPICE, TCAD, or physical PPA work was performed.

## Answers and remaining measurements

1. **How much does TAGE conditional-direction prediction reduce execution time?** UNKNOWN in these historical records. Neither clean native-versus-finite overhead nor R2 fault overhead is TAGE-versus-STATIC_NT. A direction-only STATIC_NT control consistent with target processing and speculative history remains unmeasured here.
2. **How harmful are predictor faults?** R2 provides the numerical inline-contract answers above: SOURCE mean cycle damage is 6,781.5 / 229,313.5 / 11,245.5 for qsort/dijkstra/SHA-1; atomic K2 is 151,323.5 / 42,490.5 / 0. MPKI and sample ranges are preserved separately. Reuse these as historical evidence, not as newly certified pristine-native measurements. B4 answers the corresponding question for finite P0 only.
3. **Is protection faster after normal and recovery costs?** Under R2 C0 stage fit, some conditions show net benefit; there is no universal method winner, and SHA-1 K2 ECC loses 105 cycles. B4 protection helps relative to faulty finite P0 in several conditions, while its large common clean cost remains charged versus native. Native fault B and matched full-stage timing are missing, so a general native/full-cost winner is UNKNOWN.

The three-way REFERENCE_NATIVE / NATIVE_FI_OFF / NATIVE_FI_NO_EVENTS equivalence is not established by these tables. The B4 configuration gate checks declared CPU/cache/TAGE parameters, not prediction/training/RNG trace identity across those three modes. The other chat owns the current native/causal work; no duplicate baseline, fault pilot, or STATIC_NT batch was launched in this analysis.

## Reproduction and artifacts

The reusable command is:

```bash
python -m simulation.analysis.abcd CPU_ABCD.csv --clean CLEAN_RESULTS.csv \
  --unprotected U --contract R2_INLINE_STAGE_FIT_C0 --cohort R2_EVALUATION
python -m simulation.analysis.abcd EVAL_ABCD.csv --clean EVAL_CLEAN.csv \
  --unprotected P0 --contract B4_COMMON_FINITE_P0 --cohort B4_EVAL
```

For DEV use its own pair/clean inputs and `--cohort B4_DEV`. Output is JSON with original rows, per-owner decomposition, means/ranges, signs and missing-metric counts. The command rejects duplicate owners/methods, conflicting declared contracts/cohorts, mismatched clean controls and mismatched unprotected owner cycles. It preserves invalid rows without treating them as zero-cost successes.

This run stores exact commands, source paths, owner/sample and summary CSVs, JSON, original attached CSV copies, B4 execution commands/identifiers, and the validation log outside Git at `/home/youns/radiation-aware-tage-private/historical-analysis-20261116-r1/`. B4 commands in the closed records refer to preserved historical source/binary/input/schedule identifiers; the original files are not asserted to exist locally. R2 CSV owner/condition/termination/tape fields are available, but its original per-trial command lines and full producer artifacts are not supplied.

Validation: isolated `make -j4 test` passes all C++ gates and 32 Python tests including six new analysis tests. Analysis changes do not alter gem5 or predictor code; no new gem5 checksum/performance runs were used to claim CPU correctness.
