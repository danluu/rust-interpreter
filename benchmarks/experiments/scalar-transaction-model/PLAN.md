# Bounded scalar memory transactions: model first

The read-only candidate failed its complete changed-source screen. Current
adopted-VM samples place 153 block samples in bounded leaves first rejected for
external writes, including a sparse-set update and SipHash rounds. This is an
optimistic bound, not admission or performance evidence.

Extend the internal proof/model only. Retain at most 512 bytecode operations,
512 frame bytes/registers, 16-byte argument/result boundaries, acyclic CFG,
existing work budgets and no nested Calls, allocation, FFI or unknown effects.
Permit fixed external reads/writes no wider than 16 bytes, with at most 16
external store sites. Represent each store explicitly as a live ordered effect.
Current production Call admission must not select the new mode. Native emission
must reject new store effects until a separately qualified backend exists.

Model execution uses private stores. Each external access validates its complete
original range against stable pre-Call linear/heap backing, excluding the entire
fresh callee and alignment padding. Reads observe earlier private stores with
exact byte overlap and last-write precedence. Successful execution commits
stores in original order before its result; any private failure replays the
ordinary Call before publishing effects. The model is a correctness oracle,
not the intended native hot-path implementation or a timing proxy.

Check nonoverlapping and overlapping stores, full/partial read forwarding,
read-before-write, repeated writes, every width/budget boundary, dead reads,
faults after writes, fresh-frame aliases, zero-width accesses, high address bits
and the store limit. Compare values, original PCs and externally visible memory
with the project's own reference interpreter. Keep native emission refused.

Then run a source-bound saved-artifact proof/lowering census and rejoin current
samples. A native prototype requires material surviving coverage. Its likely
implementation uses static address-family forwarding and private store slots;
uncertain cross-family aliases can decline and replay. That optimization needs
its own proof and controls. Do not remove checks or speculate about aliasing.

Keep the shared lock, two Cargo workers, protected shared ROOT target,
max(14 GiB, 8 GiB + twice allocated target) initial build admission and 8 GiB child
floor. Preserve all parked histories, installed tools, source/artifact snapshots,
peer work and the paused goal. No larger history starts for the failed candidate.
