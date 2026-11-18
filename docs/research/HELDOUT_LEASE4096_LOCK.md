# Prospective held-out SOURCE evaluation

Locked on 2026-11-17 before any held-out gem5 run or routed timing result
for the registered history implementation. Fixed methods are ordinary
unprotected recurrent TAGE and full-bank quiescent lease4096. At 4,096
speculative raw appends, stop admissions, wait for actual restore owners
to drain, then publish canonical folds from current own raw. The cadence,
all-bank mask and policy are fixed. Physical service and clock parameters
must be filled in from the rule below before opening outcomes. The online
mismatch monitor is a separate diagnostic.

## Workloads and expected outputs

Use three previously unrun MiBench programs from the [original University
of Michigan source distribution](https://vhosts.eecs.umich.edu/mibench/source.html).
Select these tasks prospectively for different kernels. No TAGE PC profiles
or held-out timing results were inspected.

| Workload | Input | Exit and output reference |
|---|---|---|
| basicmath_small | Built-in small inputs | Native x86-64 exit 0 and stdout |
| patricia | Official small.udp | Native x86-64 exit 0 and stdout |
| CRC32 | Official sample invocation uses adpcm/data/large.pcm | Native x86-64 exit 0 and stdout, checksum independently verified with zlib |

The private artifact lock is `heldout-mibench-20261117-r1/ARTIFACTS.sha256`
under the private project root. All binaries use static musl 1.2.5 and -O3.
Basicmath force-includes stdio.h. Patricia removes an unused RPC header,
uses -fcommon, and returns 0 on the terminal success path. The final
Patricia stdout matches the native original-success-path output byte for
byte. CRC32 uses a 32-bit unsigned DWORD and matching format to preserve
the original CRC width on LP64. The private sources, archive hashes, ELF
files, inputs and native expected outputs preserve the exact tested variants.

## Physical gate and clock rule

Use mapped recurrent and lease from the same RTL revision, placed and routed
at common GPDK45 constraints. Verify placed clock tree, extracted RC, setup,
hold, query, update, undo and publication paths. Verify the source/owner
protocol and that observed CPU demand fits the two-query, three-append and
512-restore-owner contract. Record a common clock supported by both designs.
The measured history lower bound is the original clock period plus the
larger nonnegative setup deficit of the two designs, rounded up to 1 ps.
Recheck timing at the chosen period and include any separately qualified
provider/operand path requirement. Convert the common period to gem5
`--cycle-ticks` in the 1 ps timebase. Use the measured implementation's
service cycles for `--lease-service-cycles`, with drain measured by gem5.
The current RTL has a two-cycle service countdown. Paths completing on
one edge must still close over that edge's timing budget.

If hold, interface dependency or provider timing is unresolved, label
any available history period a subsystem bound. It cannot establish full
CPU backannotation. A timed/scheduled change requires fresh RTL and bounded
CPU checks before opening held-out outcomes. No B0 path delay or arbitrary
extra lookup cycle substitutes for this gate. Power reports must state trace
scope and activity coverage. Component-level energy and task energy are
reported at their measured boundaries.

## Runs and decision

Use one U0 and one M0 per workload, then eight paired SOURCE owners per
workload. Workload order is basicmath, patricia, CRC32. Seed is
`202611180001 + 1000000 * workload_index + owner_index` with zero-based
indices. Predictor seed is 548. SOURCE remains 2000 events/s on raw130,
with integer K1:K2=205:9 and contiguous atomic XOR. Generate one common
absolute-tick tape per owner through eight times the longer measured
clean exit, rounded upward to a 500-tick reference grid boundary. Reuse
this tape for both arms. Stop at real program exit. Preserve future events,
zero hits, mismatches, timeouts and exhausted tapes. Predeclare a maximum
of 16 concurrent jobs and use at most eight for this CPU batch. Host limit
is 7,200 seconds per execution. Config, binary and tape hashes are recorded
before running the paired arms.

This plans six clean and 48 faulted runs after the physical and regression
gates. Validate stdout, exit status, exact retirement identity against clean
native, and equal instruction counts. Primary metric is paired percent
completion-time benefit, positive for lease, computed from simulated ticks.
Report per-workload pairs and exploratory 95% owner-bootstrap intervals,
with 10,000 draws and bootstrap seed 202611189001. Owners are the unit of
uncertainty. Report failed pairs explicitly and withhold all-owner superiority
there. The fixed three-workload suite supplies a between-workload check.
It does not define a random sample of all programs. Stop at eight owners
per workload and retain unfavourable results.

## Executable qualification and follow-up

The original artifact lock was used unchanged for the CRC32 SOURCE
comparison. The original Basicmath and Patricia executables failed
the exact host stdout gate. On November 18 the user approved a
separate glibc follow-up for those two workloads. The follow-up
kept the input bytes, required output bytes, seed ordering and
all predictor and tape parameters. The new executable and library
hashes are recorded separately. The [CRC32 results](../results/source-heldout-2026-11-18.md)
and [glibc results](../results/source-heldout-glibc-2026-11-18.md)
identify their cohorts and actual simulator producers.
