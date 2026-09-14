# Bounded exact-value scalar aliases

The qualified computation census finds 85,471,196 cast and 32,006,184 pack
computations in successful token block scalar Calls that could be exact-value
aliases. Of these, 90,326,250 occur in the copy precondition and 23,539,100 in
is_aligned_to. This is a new runtime revision on the parked dead-register
composition, compared with the unchanged adopted baseline. It does not repeat
the failed 0.949959 primary or relax its gate.

Compute conservative upper-bit bounds along the existing scalar SSA order.
Replace only casts and one zero-offset pack that provably preserve the complete
u128 value with the canonical original value. Keep original PCs, computations,
branch graph, steps, node widths and every nonaliased live node. In particular,
retain Div/Rem roots even when their result is unused. Do not add a general
constant folder or remove other dead code. Signed widening is an alias only
when the source cannot have its sign bit set.

The native emitter simplifies a private clone; the original scalar plan remains
an independent reference evaluator. Bound nodes at 16,384 and all traversals at
250,000 work units. Nonconforming order or excess work preserves the preceding
emission. Clone, proof, allocation and emission cost remain inside JIT setup.
No frontend/checking/Call transaction/CLI/default changes or foreign guest
backend are introduced. Scalar Calls remain explicit opt-in.

Compare the new engine with spilled, allocated and preceding dead-register
native bodies plus the original scalar evaluator. Cover signed values, full
u128 results, aliases, phis, register pressure, private faults and every budget
tail. Qualify 22 focused tests and 600 workspace passes in each profile (13
ignored), strict Cargo and cache negatives, and the six original profiles.
Only then run the unchanged forty-command primary. Full comparisons and parser
work remain conditional on a passing primary; no adoption from this census.

Use the same source-root shared target and two Cargo workers. Require the
existing max(14 GiB, 8 GiB plus twice allocated target bytes) build admission,
14 GiB screen admission and 8 GiB child floor under the benchmark lock. Never
clean the shared target, installed tools or any other workstream.
