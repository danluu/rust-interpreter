# Native path candidate qualification

The experimental branch `experiment/scalar-path-guards-20260914` now has a
qualified direct AArch64 implementation of the path certificate model. Main
continues to use adopted tool `df4006e0`; this qualification establishes no
performance improvement.

The guard follows the actual acyclic path before changing guest memory. It
checks addresses, assertions and fallible arithmetic, and retains the values
needed to establish that path. A captured read must be disjoint from every
earlier visited write. A failed guard takes the ordinary Call path before any
effect. Successful execution consumes the retained values, performs the remaining
reads and stores in original order, and cannot replay after committing a store.
An internal certificate failure returns a distinct VM error.

The native controls compare complete memory, error exits, instruction counts
and peak memory against the interpreter in both persistent-register modes.
They cover all store widths through 16 bytes, aliases, full-width conditions and
pointers, late assertions/division/traps, budget tails, heap-free execution,
padding, resource limits and an injected post-store invariant failure. The
second control run passes 44 tests in each build profile and 14 additional
entry/order controls. The full candidate build passes 681 workspace tests in
each profile (21 ignored), plus 407 Python tests (22 declared skips).

Immutable tool
`69005a3751a97908ed1cbcd4293613014cb63f6e388c768afc15d8fda00adcc6`
uses build source `b10dd5b8c503c00b606f7a0d11c3b14f1fc0bedc`. Its exporter,
wrapper and compiler match the adopted control exactly. All 121 strict/cache
commands pass, including unreachable type/borrow error rejection and rejection
of actual partial-checking artifacts.

Three new original-test diagnostic profiles pass against three exactly bound
adopted profiles. Outputs/assertions, every logical instruction count, peak
memory, entropy and reconstruction of all generated native bytes agree.
Successful scalar Calls are 27,650,466 for token block, 16,416,150 for token
exhaustive and 1,585,160 for folded matching. These counts match the earlier
store-log candidate; they are coverage evidence, not timing evidence.

The preregistered next step is one 40-command changed-source token comparison,
with five successful edited pairs, an A/A control and ordinary native Rust.
Profiling and the entropy shim are excluded from timing. The existing gate
determines whether to run the full five-project comparison and both parser
guards. A failed primary cancels those larger runs. Main's runtime remains
unchanged while this decision is pending.

Evidence: [native controls](../results/scalar-path-native-02/summary.json),
[build](../results/scalar-path-build-01/summary.json),
[strict checks](../results/scalar-path-qualification-01/summary.json),
[profiles](../results/scalar-path-profile-01/summary.json),
[screen protocol](../benchmarks/experiments/scalar-path-screen/SCREEN.md).
