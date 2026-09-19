# Separate large-frame stores from dynamic clear-loop overhead

The small-frame overlap candidate is PARKED after a complete inconclusive ES8
real-edit comparison (medianwall0.994215, full A/A10.44%). Production is restored
to adopted24cd8e99 before this new scope. Do not retry it unchanged or infer a
performance gain from native-code shrinkage.

Reuse CLOSED ordinary-padding-scope02 typed layouts and its four original saved
self-PC captures. For every ordinary callee payload>256, require the exact adopted
20-word64-byte-batch plus general-tail helper, ending at the clear span boundary.
Partition its exact PCs into setup,64-byte stores,64-byte loop control,16-byte
stores/control, and byte stores/control. Keep the preceding ordinary setup words
separate. Reject mutated/unaligned helpers and verify branch displacements. Reconcile
all original ordinary-clear samples, preserve ambiguity and ineligible alignments.
Report static sizes and typed hot sites without duplicating all site rows in summary.
No new guest, compiler build, code publication or timing measurement.

Question: does compile-time payload knowledge offer material coverage beyond the
parked small-frame mechanism? A possible later candidate would run a fixed-count
64-byte loop over P, emit its exact compile-time residual stores, and cover bounded
actual padding with an end-anchored A-byte store for A<=16. Static empty-padding
proof can avoid that extra store. Existing guards/initialized padding/strict checking
would remain obligations. This scope does not implement or authorize adoption of
that runtime change; stores already required by semantics are not claimed removable.

Bind complete closed inputs, historical source evidence and original map validation.
Pure matcher controls precede capture classification; independent closure recomputes
every count and hash. Shared45s lock,12GiB admission, zero children, no other-session
interference or goal changes. Freeze through terminal and independent closure.
