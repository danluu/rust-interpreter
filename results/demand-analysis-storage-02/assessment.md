# Compact masks remove most proposed retention

Both focused storage controls and the three saved artifact observations pass.
The same source as the complete native/emission qualification is used. Five
commands take 3.557323 seconds; the closure verifies 247 source/input bindings
and 13 output artifacts. No guest code or executable publication occurs.

| Scope | Previous buffer/box/inline bytes | Compact retained bytes | Reduction |
|---|---:|---:|---:|
| All token functions | 282,159,980 | 33,561,161 | 88.11% |
| Captured block ordinary functions | 69,453,464 | 7,507,618 | 89.19% |
| Captured exhaustive ordinary functions | 85,443,908 | 9,515,312 | 88.86% |
| All folded functions | 90,101,764 | 7,000,455 | 92.23% |
| Captured folded ordinary functions | 18,060,892 | 1,306,785 | 92.76% |
| All current full-parser functions | 107,938,424 | 26,874,018 | 75.10% |

These are matched retained-payload inventories, not RSS or simultaneous runtime
working sets. The compact inventory excludes full liveness buffers kept only
under cfg(test) for diagnostic oracles; it reports their bytes separately. Inline
struct counts still include the test-only liveness header and therefore overstate
production. BTree nodes, allocator costs and transient analysis remain excluded;
unchanged map-entry tuple payload is separately reported in the summary.

Adopt a 16 MiB prospective per-JIT retained-analysis charge for the demand
prototype, with eager fallback on refusal. First replace retained BTree hints
with sorted owned vectors so all retained buffers can be accounted without node
estimates; qualify lookups, budget boundaries and exact emission. The measured
captured subsets fit that proposed budget, but encounter order and additional
publication metadata can still cause fallback. No latency gain or runtime
adoption follows from this storage reduction.
