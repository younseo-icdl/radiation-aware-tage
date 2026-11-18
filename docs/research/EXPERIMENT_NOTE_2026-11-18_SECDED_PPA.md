# Matched history-block SECDED and lease4096 PPA

## Implemented boundary

The staged history block retains its history ring, head, path
checkpoint array, undo and append interfaces, registered query, and
returned-row selection. The SECDED arm protects the established
S* payload of 346 logical bits: the active raw130 word, 21 folded
words totalling 200 bits, and current path16. It adds 121 stored
check bits and a sticky uncorrectable-error latch. Head, older
retained raw ages outside the current 130-bit window, checkpoint
rows, and external predictor arrays remain outside this code
coverage. They are still present wherever they belong to the
measured history boundary.

The decoders feed corrected data directly into the query and
history RMW paths. A clean history operation re-encodes its final
raw, fold, and path values. On an idle edge a correction can
write back the affected raw bit or carry corrected fold, path,
and check bits back to storage. A corrected raw payload bit is
forwarded into a simultaneously restored view when that view
still contains the bit. An append to the same physical ring
row takes priority over repair of the old value. A detected
uncorrectable word disables admission and state mutation until
reset. This is the measured RTL containment behavior. A CPU
fallback/refill implementation is outside this physical block.

## First gates and measurement conditions

Xcelium passed the directed raw/fold/path and check-bit read and
writeback controls, including undo, an append collision, and a
same-word double error. Clean stimulus replay passed 80,001
edges and 14,519 returned-row predictions per arm. Both arms used
the same lease-generated input vectors. The four lease maintenance
windows are electrically idle input cycles in the ECC arm. There
is no injected fault in this common activity window. Faulted
writeback is verified in the directed gate.

Fresh Genus and Innovus producers use the same GPDK45 libraries,
clock and I/O constraints, and initial 543.349 µm core width and
height. The first timing test uses a common 13.850 ns period,
including the existing 6.641 ns row and 9.582 ns target-valid
late arrivals. Require 65–75% die utilization, DRC and both
connectivity checks before accepting a routed case. Extracted
setup, hold, query, and returned-row timing determine whether
the initial period is feasible. Compare activity-based power
only at a common qualified period and on identical input edges.
Track zero-delay gate activity and annotation coverage separately
from extracted timing. Raw logs and independent producers are
under `work/history-secded-ppa-20261118-r1/`.

The standalone C++ suite and 70 Python checks passed. The
existing checksum-qualified gem5 executable also passed all 14
finite checksum cases. Its P_ECC case validates the software
model. The Xcelium test and trace replay establish the separate
RTL and do not change the gem5 integration.
