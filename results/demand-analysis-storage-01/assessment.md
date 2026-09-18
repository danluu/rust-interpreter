# Full liveness dominates proposed retained analysis

The observer validates the exact saved 5,468-function token, 1,048-function
folded-text and 11,832-function current full-parser graphs. One focused storage
control passes in each profile, followed by three successful saved observers.
Five commands take 22.149920 seconds of setup/qualification. The closure verifies
243 source/input bindings and 13 output artifacts. No guest code executes.

| Scope | Vec/box/inline bytes | Liveness bits | Successor vectors | Map entry tuples (separate) |
|---|---:|---:|---:|---:|
| All token functions | 282,159,980 | 205,784,880 | 43,695,672 | 584,064 |
| Captured block ordinary functions | 69,453,464 | 51,140,768 | 11,011,152 | 156,032 |
| Captured exhaustive ordinary functions | 85,443,908 | 62,878,272 | 13,306,920 | 183,360 |
| All folded functions | 90,101,764 | 72,249,784 | 11,059,384 | 128,896 |
| Captured folded ordinary functions | 18,060,892 | 14,659,264 | 2,134,272 | 21,760 |
| All current full-parser functions | 107,938,424 | 49,460,376 | 32,107,904 | 919,040 |

The captured subsets are exact ordinary-function IDs from adopted profiled code
maps; the inventory includes each such function's complete analysis, including
unsupported operations. These are potential retained payload sums, not an
encounter sequence, simultaneous working set, RSS or a timing measurement.
BTree node occupancy/links, allocator overhead and transient analysis work are
excluded; map entry tuple estimates are reported separately from counted buffers.

Production emission consults liveness only for its at-most-three assigned
persistent registers when spilling continuations. Full-register liveness and
successor graphs remain necessary during fixed assignment analysis and for
existing offline diagnostics, but need not remain in a runtime emission plan.
Next retain a per-PC bit mask for the selected registers after the original
bounded analysis, leaving assignment and generated words unchanged. Requalify
native controls and exact captures, then inventory the compact representation
before setting an aggregate retention budget and implementing demand publication.
