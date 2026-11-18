# Matched SOURCE held-out result, November 18, 2026

On CRC32, the fixed full-bank lease4096 suppressed most of the
radiation-induced runtime overhead. Its clean maintenance cost exceeded
the savings at the evaluated event rate. Ordinary unprotected TAGE
completed faster in all eight faulted pairs. Basicmath and Patricia
failed the exact clean-output criterion and contributed no faulted
performance pairs.

## Timing, power, and execution scope

The GPDK45 history layouts closed the common 13.850 ns clock with
72.979% recurrent and 72.630% lease die utilization. The independently
routed direct-target BTB reference used 69.821% and measured an
8.578 ns read-to-hit delay. The composed target arrival was 9.582 ns,
with +330 ps setup slack in the limiting lease layout. The model used
one cycle for hash capture, one cycle for row response, a single
conditional training admission per cycle, and two publication service
cycles after observed restore-owner drain. Timing and activity scope
are detailed in the [staged-query note](../research/EXPERIMENT_NOTE_2026-11-17_STAGED_QUERY.md).

On the clean 80,001-edge checksum activity window, recurrent and lease
history layouts used 2.389 and 2.517 µJ respectively. The estimate
covered all routed nets and flop outputs with zero cell delay.
The layouts differ in placed history cell area by -0.48% for lease.
The activity replay estimates history-block energy in its own clean
checksum window. No CRC32 energy was measured.

The exact held-out simulator passed four x87 probes, 14 finite checksum
cases, 21 timed checksum cases, and 11 cross-checks. The study audit
verified the canonical overlay and the x87 compatibility patch. Each
CRC32 output matched the locked host bytes, and all cases preserved
the 507,879,258-instruction stream and zero indirect conditional
lookups required by this reference. The maximum live history owner
count across the faulted cases was 24. The protocol and artifact
selection are in the [prospective lock](../research/HELDOUT_LEASE4096_LOCK.md).

## CRC32

| Clean arm | Cycles | IPC | Branch misses | Lease publications |
|---|---:|---:|---:|---:|
| Ordinary recurrent TAGE | 428,544,397 | 1.185126 | 26,341 | 0 |
| Full-bank lease4096 | 428,915,731 | 1.184100 | 26,341 | 32,675 |

Clean lease cost was +371,334 cycles (+0.086650%). Each owner supplied
the same absolute SOURCE tape to both modes. The tape law is 2,000
events/s on raw130, atomic XOR, contiguous placement, and K1:K2 =
205:9. Architectural exit censors later events, so applied counts can
differ across arms even though their tapes are identical. Delivery,
censoring, retirement and publication were audited in all 16 runs.

| Owner seed | Ordinary cycles | Lease cycles | Ordinary / lease events | Ordinary / lease branch misses | Lease benefit |
|---|---:|---:|---:|---:|---:|
| 202613180001 | 428,712,460 | 428,915,839 | 12,083 / 12,085 | 41,301 / 26,348 | -0.047439% |
| 202613180002 | 428,702,555 | 428,916,000 | 11,992 / 12,002 | 40,457 / 26,357 | -0.049789% |
| 202613180003 | 428,707,111 | 428,915,962 | 11,930 / 11,932 | 40,876 / 26,359 | -0.048716% |
| 202613180004 | 428,706,080 | 428,916,181 | 11,748 / 11,757 | 40,765 / 26,371 | -0.049008% |
| 202613180005 | 428,706,626 | 428,915,839 | 11,789 / 11,793 | 40,838 / 26,350 | -0.048801% |
| 202613180006 | 428,706,373 | 428,915,839 | 11,811 / 11,818 | 40,784 / 26,350 | -0.048860% |
| 202613180007 | 428,712,942 | 428,915,931 | 11,888 / 11,893 | 41,409 / 26,356 | -0.047348% |
| 202613180008 | 428,703,957 | 428,915,863 | 11,935 / 11,940 | 40,606 / 26,353 | -0.049429% |

Benefit is 100 × (ordinary faulted ticks − lease faulted ticks) /
ordinary faulted ticks. The mean was **−0.048674%**, with exploratory
95% owner-bootstrap interval **[−0.049202%, −0.048091%]**. Lease took
208,669 more cycles on average. There were zero failures, timeouts,
or noncomparable owners. The eight owners describe the fixed CRC32
and SOURCE experiment.

Faults increased ordinary runtime by +0.038004% over its own clean
reference and lease runtime by +0.0000468% over its clean reference.
Ordinary branch misses increased from 26,341 to a mean of 40,879.5
(+14,538.5); the lease mean was 26,355.5 (+14.5). Thus the mitigation
substantially reduced prediction disruption and the incremental fault
cost. On CRC32 its clean cost was larger than the fault tax it
removed. This establishes the throughput tradeoff on an untouched
workload, alongside the separate development gains reported for
[qsort](source-development-2026-11-17.md).

## Ineligible workload outputs and evidence locations

On the x87 compatibility build both Basicmath and both Patricia clean
runs terminated successfully and produced identical bytes within
each paired configuration. The host byte check failed for 9,905 of
19,733 Basicmath lines and 10,437 of 10,440 Patricia lines. The Patricia
differences were confined to the printed input-time field. The frozen
artifacts and the failure reports remain intact. No SOURCE performance
claim uses either workload.

The ignored local directory `work/heldout-source-20261118-r3/`
contains `ADMISSION.json`, `CLEAN.json`, `CLEAN_PROVENANCE.json`,
`FAULTED.json`, `SUMMARY.json`, `crc32-pairs.csv`, tape digests,
per-case logs, output and delivery records. The reused exact clean
archive is `heldout-source-20261118-r2/` under the private experiment
root. The timed checks and issue contract are under
`work/heldout-admission-20261118-r8/`.
