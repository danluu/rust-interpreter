# Temporal address dependencies broaden coverage modestly

Fourteen controls pass per debug/release profile, including temporal write-set
oracles and the division overflow-projection correction. All 245 archived
store-log bodies reconstruct exactly. No guest runs or native publications occur.
The closed first and corrected censuses admit the same 17/20/1 functions.

The exact adopted-sample join finds 23 Call/Return and 39 body samples in block
(62/1,561 generated samples), and 0/1 in exhaustive (1/1,231). The broader rule
adds only 19 block samples over captured inputs plus constants. This still counts
whole bodies and ignores dynamic alias declines and guard overhead. It is not a
speedup estimate. Do not wire this static policy into native execution alone.

The sparse-set update remains excluded because assertions and a trap can occur
after writes. To reach it safely, the next model must certify the actual path
before effects. A bounded guard slice can evaluate only address/control/fault
dependencies, check every visited memory range, and reject reads that overlap
prior visited writes. It can therefore establish that the later execution will
follow the certified path without a fault; any failed certification replays the
original Call before a store occurs. Phi values must follow their actual incoming
edge. Memory-derived values modified by prior writes continue to decline.

This is a new model obligation, not an exception to fault preservation. Validate
complete successful/error-exit memory, every budget tail, captured inputs,
fresh frames, padding, readonly ranges, heap boundaries and non-idempotent stores
against the ordinary interpreter before any emitted guard or direct store.
