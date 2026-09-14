# Every retained plan buffer now has an exact payload charge

The focused inventory controls pass in both profiles, followed by all three saved
graph observers. Five commands take 3.933398 seconds; the closure verifies 252
source/input bindings and 13 output artifacts. Every function's independent field
inventory exactly equals its checked retention charge. No retained BTree node
estimate remains: hints now use counted sorted vectors.

| Scope | Charged plan payload bytes |
|---|---:|
| All token functions | 34,145,225 |
| Captured block ordinary functions | 7,663,650 |
| Captured exhaustive ordinary functions | 9,698,672 |
| All folded functions | 7,129,351 |
| Captured folded ordinary functions | 1,328,545 |
| All current full-parser functions | 27,793,058 |

These totals exclude the pool index/header (charged separately by the pool),
allocator rounding, transient analysis and later publication metadata. Inline
headers use the test layout, while test-only full-liveness buffers are explicitly
separated. The totals do not give encounter order or simultaneous runtime use.
All token/parser functions would exceed the 16 MiB plan budget; refusal must use
eager emission. Captured token subsets fit, without proving the eventual demand
run will admit the same functions or improve latency.

Next implement the checked code append/edge-patch transaction under the existing
single-thread ownership contract, then stable entry tables and bounded pending
edges. Preserve fault order, exact logical counts and original Rust checking.
