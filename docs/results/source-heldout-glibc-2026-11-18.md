# Held-out Basicmath and Patricia glibc follow-up

At the fixed SOURCE rate, lease4096 completed faster in all eight
Basicmath pairs and all eight Patricia pairs. The mean improvements
were 4.159667% and 5.179958%. The original static musl executables
remain ineligible under the exact stdout rule. The completed
[CRC32 cohort](source-heldout-2026-11-18.md) used its original
locked musl executable and showed a small runtime loss for lease4096.

## Qualification and protocol

The user approved a separate follow-up with the same source and input
and glibc-linked executables. Each executable reproduced the original
locked host stdout byte for byte. The private manifest records
executable and input hashes, both reference outputs, and the dynamic
loader, libc and libm hashes. Basicmath and Patricia retained the
original workload indices, eight paired owner seeds each, and the
prospectively locked lease4096 policy. The original clean failures,
the initial glibc front-end failures, and the candidate executables
are preserved separately.

The final paired runs used the corrected staged gem5 O3 build and the
GPDK45-qualified 13.850 ns period. Each conditional query used one
hash-capture cycle and one row-response cycle. The retirement port
admitted one conditional training reservation per cycle. Lease
publication used two service cycles after observed restore-owner
drain. The front-end correction aligned request admission with BPU
branch classification for x86 internal microbranches. The 14 finite
checksum cases, 23 timed cases and 12 timed cross-checks passed. All
21 previous bounded native case observations and the four history
activity traces were byte-identical. The archived CRC32 runs report
zero lookups in the microbranch class affected by the correction.

All four clean cells and 32 faulted cells passed exact stdout,
architectural retirement identity, timing contracts, and delivery
checks. No run timed out or used indirect conditional lookups. The
largest observed restore-owner count was 41. The event tapes were
generated before the faulted runs, with horizon eight times the
longer clean exit rounded up on the fixed 500 ps grid. Each pair
shared its absolute SOURCE tape at 2,000 events/s on raw130,
using atomic contiguous XOR and K1:K2 = 205:9. Different exit
times can yield different applied event counts from a common tape.

## Clean controls

| Workload | Retired instructions per arm | Ordinary cycles | Lease cycles | Ordinary IPC | Lease IPC | Lease cost |
|---|---:|---:|---:|---:|---:|---:|
| Basicmath | 51,416,894 | 57,639,766 | 57,671,810 | 0.892039 | 0.891543 | +0.055594% |
| Patricia | 73,714,108 | 85,117,221 | 85,159,564 | 0.866030 | 0.865600 | +0.049747% |

## Faulted pairs

Benefit is 100 × (ordinary faulted ticks − lease faulted ticks) /
ordinary faulted ticks. The exploratory 95% percentile intervals use
10,000 bootstrap draws over the eight paired owners of each workload.

| Workload | Valid pairs | Mean lease benefit | 95% owner-bootstrap interval | Pairs favouring lease |
|---|---:|---:|---:|---:|
| Basicmath | 8/8 | +4.159667% | [+4.126559%, +4.194265%] | 8 |
| Patricia | 8/8 | +5.179958% | [+5.143109%, +5.219713%] | 8 |

### Basicmath

| Owner seed | Ordinary cycles | Lease cycles | Ordinary / lease events | Lease benefit |
|---|---:|---:|---:|---:|
| 202611180001 | 60,360,462 | 57,804,287 | 1,627 / 1,545 | +4.234850% |
| 202611180002 | 60,298,558 | 57,815,953 | 1,735 / 1,661 | +4.117188% |
| 202611180003 | 60,299,595 | 57,819,016 | 1,669 / 1,605 | +4.113757% |
| 202611180004 | 60,365,547 | 57,816,918 | 1,660 / 1,582 | +4.221993% |
| 202611180005 | 60,306,183 | 57,811,989 | 1,589 / 1,509 | +4.135884% |
| 202611180006 | 60,324,546 | 57,818,341 | 1,663 / 1,600 | +4.154536% |
| 202611180007 | 60,277,487 | 57,806,844 | 1,674 / 1,613 | +4.098782% |
| 202611180008 | 60,353,218 | 57,818,173 | 1,660 / 1,585 | +4.200348% |

### Patricia

| Owner seed | Ordinary cycles | Lease cycles | Ordinary / lease events | Lease benefit |
|---|---:|---:|---:|---:|
| 202612180001 | 89,994,039 | 85,335,117 | 2,492 / 2,365 | +5.176923% |
| 202612180002 | 89,981,214 | 85,331,830 | 2,410 / 2,294 | +5.167061% |
| 202612180003 | 90,035,180 | 85,350,609 | 2,554 / 2,411 | +5.203045% |
| 202612180004 | 89,912,560 | 85,338,443 | 2,426 / 2,288 | +5.087295% |
| 202612180005 | 89,950,291 | 85,333,181 | 2,496 / 2,360 | +5.132957% |
| 202612180006 | 90,025,192 | 85,346,071 | 2,490 / 2,360 | +5.197568% |
| 202612180007 | 90,102,439 | 85,335,002 | 2,477 / 2,358 | +5.291130% |
| 202612180008 | 90,009,678 | 85,343,863 | 2,519 / 2,391 | +5.183681% |

## Workload dependence

| Workload and executable | Ordinary fault cost | Lease fault cost | Ordinary added misses | Lease added misses |
|---|---:|---:|---:|---:|
| Basicmath glibc | +4.655525% | +0.246446% | 277,618.4 | 13,846.0 |
| Patricia glibc | +5.738090% | +0.211016% | 539,236.3 | 19,246.4 |
| CRC32 locked musl | +0.038004% | +0.000047% | 14,538.5 | 14.5 |

Fault cost and added misses are relative to each arm's own clean
reference and averaged across its eight runs. The reduction in
misses accompanies the reduced execution cost for both glibc
workloads. CRC32 encountered many more injected events per run
yet accumulated far fewer excess misses. This illustrates why
injection count alone does not predict performance impact.
The clean cost explains the sign change in net runtime when the
recurrent predictor suffers little fault-induced delay. The table
preserves executable provenance and supplies no cross-workload
average or prediction of population-wide superiority. It does
not resolve which specific CRC32 branches account for its lower
fault cost. The available power numbers come from the cleaned
history-block checksum replay, so this experiment supplies no
per-workload or whole-CPU energy result.

Raw stdout, per-case status and counters, termination records,
paired seed tables, tape digests, and SOURCE delivery logs are in
`work/heldout-glibc-followup-20261118-r1/evaluation-owner-fix/`.
The source and regression audits are under
`work/gem5-frontend-owner-fix-20261118-r1/`.
