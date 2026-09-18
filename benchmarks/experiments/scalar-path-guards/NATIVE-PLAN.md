# Emit checked paths and reuse their values in a direct-effect phase

The 32-control model and exact saved-body/sampling censuses are closed. Native
work remains experimental until full qualification and a changed-source primary.
Use this project's AArch64 emitter and existing private scalar Call ABI only.

Emit two phases sharing one bounded private stack allocation. The guard phase
walks the original CFG using the qualified address/control/fault dependency slice.
Check all visited ranges against the pre-Call linear prefix/current heap and
write protection. Track at most sixteen active checked host write ranges. A
captured read must be disjoint from all earlier active writes before loading.
Keep captured scalar values in unique per-node slots, reusing existing spill
slots where safe; inputs/constants/base addresses remain rematerializable.

The commit phase consumes those values, skips their computations and selected
phis, and preserves every remaining read/store/result effect in original order.
Its memory accesses use the already certified addresses and widths. Charge exact
original PCs in private Output only once, during guard traversal; publish only
after successful Return. Guard failure returns the existing decline status before
any effect. A commit-phase invariant failure must use a distinct non-replay
status and restore the parent ABI before returning an internal VM error. Never
route that status through the ordinary Call fallback.

Keep original allocator registers, full u128 lanes, caller-SP argument/output
layout, stack alignment, arena/code limits, finite work/shape caps, readonly/null
rules, frame/result/resource guards, padding and peak memory behavior. Filter
phi transfers by phase. Do not infer reusable values across Calls or from numeric
pointer ranges. Ordinary source type/borrow checking stays complete.

First use test-only native selection and qualify against the ordinary interpreter,
closed scalar model and old native reference across aliases, fault order, every
budget tail, wide values, phis, captured inputs, result aliases, preserved registers,
heap-free ABI, fresh frames and bounded declines. Inject the invariant status to
prove it cannot replay or mutate twice. Run full required Rust/Python/strict
checks before installing any candidate. Then obtain exact original workload
profiles and a fresh preregistered primary; no historical failure is retimed.

Use ROOT target only, shared lock, two workers/test threads, conservative
max(14 GiB,8 GiB+twice allocated target) admission and 8 GiB child floor. Preserve
all peer work and every failed command. Main remains on the adopted runtime.
