# Per-attempt guard values survive direct effect execution

The updated model passes all 32 Call controls in debug and release: ten path
controls and 22 retained scalar/private-store/native-reference controls. The
initial 31-control model is separately closed. Every new path control compares
complete active linear/heap memory on success and error, return values, error
text, peak memory, exact instruction counts and per-PC profiles against the
ordinary interpreter. Budget/resource tails preserve fallback behavior.

A certificate retains its computed SSA values only for the uninterrupted Call
attempt. Commit skips those computations and selected phis, while uncached reads
and all stores keep their original order. A dedicated control preserves a full
u128 pointer value, proves the address-producing read is not repeated, and proves
an overlapping post-store payload read still occurs. A read of memory modified
by an earlier visited write declines certification before mutation. Unexpected
failure after any committed store is an invariant violation, never a replay.

The closed exact archived-body census covers all 245 stored native bodies. Its
21/24 eligible block/exhaustive functions join to 39 transition + 99 body samples
in block (138/1,561), and 0 + 1 in exhaustive (1/1,231). These are whole-function
samples, not removable time. Dynamic guard success is not yet measured. Sparse
set update has 75/80 live nodes in its guard slice; retaining their values avoids
executing that slice twice. SipHash has 32/87 slice nodes and no captured reads.

Proceed to an isolated native prototype using this project's own AArch64
emitter: checked guard phase, stable per-attempt value slots, then commit phase.
Preserve fallback only before effects; add an explicit non-replay invariant
failure path in the native bridge. Full native/ABI/memory/budget controls and
original workloads must pass before a fresh changed-source primary. Main keeps
the adopted runtime; no speedup or native-path qualification is claimed here.
