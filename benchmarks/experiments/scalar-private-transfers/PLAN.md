# Scalar private transfer specialization

The source-qualified census reconstructs all 137 private-ABI bodies. In the
original token block test it counts 6.76 million fixed-step successful calls,
6.32 million zero-byte results and 38.23 million narrow argument captures.
These overlapping counts guide one private-transfer candidate; they are not a
hardware measurement or predicted speedup. The prior private ABI screen failed
and remains parked. The adopted runtime is still the performance control.

Reuse scalar lowering's bounded topological traversal to compute the shortest
and longest structural paths reaching Return. A fixed success count requires
equality. Keep maximum_steps over all paths, including traps, for the unchanged
entry budget guard. Immutable entry metadata replaces the private dynamic step
counter only for fixed-success leaves; all other leaves retain dynamic counting.
Reconstruct and compare that metadata along with each saved native body.

Capture only the readable argument lanes: zero bytes need none, up to eight
bytes need only the low lane, larger values keep both. Preserve original address
guards and exact odd-width reads. Omit result/destination transfers for zero-
byte returns. Original-PC profiling, private failure replay, Call/Return counts,
padding zeroing, peak/resource bounds and all guest-visible behavior remain.
Unused private Output fields stay unconsumed. Standalone scalar emission keeps
its original Output contract; the old private ABI remains a test reference.

Qualify the independent path-length observer against all saved bodies, 23
focused controls/profile and 600 workspace controls/profile (13 ignored). Add
all 0..16-byte capture widths with alias/high-lane/fault/empty-input cases, and
zero-result fixed/unequal/long-fault paths across instruction/frame/memory tails.
Then run 121 strict Cargo/cache commands, six exact original-test profiles and
the unchanged 40-command changed-source primary. Only a passing primary permits
full project and parser comparisons. Do not relax gates or retime unchanged code.

Use the shared lock, two Cargo workers, same-source shared target and conservative
14 GiB (or 8 GiB plus twice target allocation) admission. Preserve full checking,
bytecode format, CLI/defaults, peer ownership and all benchmark evidence.

The capture matrix explicitly initializes the complete return value after
reading each argument. Native eligibility remains limited to the existing
0/1/2/4/8/16-byte boundary widths; odd widths are checked for exact fallback.
The initial fixture's unwritten return tail correctly declined and its failed
native-commit assertion is retained as focused-01, not a guest mismatch.
