# Ordinary region emission has substantial uncharged coverage

Six partition/counter controls pass. All three adopted profiles and their own
native maps/code reconcile exactly, including scalar work and every published
ordinary region. No guest runs or runtime changes occur.

| Original profile | Ordinary regions | Regions with no recorded work | Ordinary bytes | Bytes with no recorded work |
| --- | ---: | ---: | ---: | ---: |
| Token block | 20,033 | 8,462 | 11,937,992 | 5,154,560 (43.18%) |
| Token exhaustive | 23,406 | 9,695 | 14,495,508 | 5,931,156 (40.92%) |
| Folded prefilter | 3,382 | 1,406 | 1,977,304 | 847,104 (42.84%) |

There are also 27 / 27 / 55 regions with interpreted work but no charged native
entry, using 19,376 / 19,324 / 43,668 bytes. Keep these separate from the table's
no-work bucket. A region may decline during preflight before its counter; no
aggregate counter proves that its entry was never visited. These are profiled
bytes, including instrumentation and fallback tails, not removable unprofiled
instructions or preparation time. Scalar body totals remain exact and separate.

Whole-profile JIT compile counters are 114.72 / 139.64 / 22.25 ms. They come from
instrumented single-test diagnostics, not the prepared edited-source workflow.
The separate closed preparation census measured about 157 ms for the largest
worker in token's complete command. Do not multiply either duration by the cold
byte fraction: liveness, slot hints, scalar-callee preparation and other whole-
function work need not shrink proportionally. Finer compilation adds first-visit
VM exits and publication costs; aggregate profiles contain no encounter order.

The size coverage justifies a bounded demand-region prototype, not adoption.
First separate immutable per-function analysis from emission while reproducing
current words exactly. Then publish reached regions and repair pending native
edges only outside guest execution, retaining fixed per-function register
assignments, arbitrary-entry safety, checked relocations and existing fallback.
Keep default full-function behavior available for controls. The prototype must
account for its retained analysis memory and analysis/publication time, and pass
full semantic qualification before the unchanged changed-source primary.
A failed primary cancels larger histories; every project and parser guard remains
required for adoption. The old parser decline is historical motivation only,
not evidence that the current parser workload gets faster.
