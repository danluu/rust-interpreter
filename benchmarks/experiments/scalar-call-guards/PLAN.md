# Guarded scalar call boundary

This revision composes the parked scalar local-register emitter with two
boundary changes. It remains explicitly opt-in; the adopted VM is the matched
control. The earlier 40-command local-register screen improved wall time by
4.00% inside a 7.63% identical-control envelope and did not authorize adoption.
No unchanged timing repeat is planned.

Scalar calls now reuse the ordinary JIT's caller-frame slot hints. Hints must
be bounded within the live caller frame and must equal the actual runtime
argument address. A mismatch takes ordinary address validation; any invalid
preexisting argument declines the transaction before guest mutation. Result
writes retain their separate write guard. Capacity, argument-copy ordering,
retained padding, error order, and logical counts are unchanged.

The private scalar entry omits its duplicate budget check only after the Call
boundary checks maximum leaf steps plus the Call. Standalone native scalar
entries still check their own budget. Immutable entry metadata and independent
code reconstruction use the same scalar plan.

Before any timing: 18 focused controls in both profiles, the full workspace,
strict-checking/launcher negatives, and six original-artifact profile commands
with exact original-PC counts, outcomes, memory, entropy and code mapping.
The new direct-entry control skips the caller's Local prefix deliberately,
covering stale hints, arbitrary high address bits, heap/readonly/invalid
addresses, large register offsets, both profile/register modes, insufficient
capacity and every budget tail. It compares complete native state with hints
disabled and enabled and verifies that a scalar entry was actually prepared.

Keep the prospective 40-command primary gate and five edited/A-A pairs.
Only a pass authorizes the larger public/private and parser comparisons.
Two Cargo workers, the original shared target and conservative 14 GiB minimum
build admission remain. No compiler cache, dependency, frontend, type/borrow
checking, artifact format, or guest Rust source changes are part of the runtime
revision. New detailed manifests remain under .work with compact Git receipts.
