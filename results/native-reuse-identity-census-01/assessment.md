# Native identity reuse has substantial edit-dependent invalidation

The census passed five controls and inspected 17 typed, fully validated artifacts
from two closed 40-command primary histories. It ran no guest, changed no
production runtime and published no executable code. Closure verifies 273 inputs
and 23 result artifacts. Setup and observation took 16.70 seconds in two commands.

| Median over five genuine successful edits | Token | Full parser |
| --- | ---: | ---: |
| Functions in edited graph | 5,468 | 11,832 |
| Exact complete bodies at the same ID | 3,366 | 9,178 |
| Exact body plus direct callee layouts | 3,366 | 9,177 |
| Exact body plus direct callee bodies | 2,349 | 7,955 |
| Exact transitive direct-call closure | 1,511 | 6,558 |
| Whole-graph diagnostic fingerprinting | 29.84 ms | 30.13 ms |
| Retained largest-worker JIT compilation | 155.75 ms | 127.96 ms |
| Retained complete command | 3.969 s | 1.641 s |

Edits 2 and 3 preserve 5,454 token bodies and 11,831 parser bodies. Other edits
change many more bodies, while data/static contents also change. This correlation
does not identify which opcode fields changed or prove that every changed value
is a relocated address. The deliberately wrong edit and restoration remain
visible in the raw comparison; they are excluded from these five-edit medians.

The saved unprofiled code maps add a narrower observation: exact identities that
also match the map's own original artifact cover median 2,415,788 token bytes and
3,339,528 parser bytes before direct dependency conditions. These are intersections
with historical code ownership, not the total native bytes reusable between two
edited artifacts. Changed functions absent from that intersection may still
reuse code between later edits. Do not turn these counts into predicted time,
cache hit rates or a claim that caching cannot help.

A complete native cache needs more than these conditions: generator/options,
current scalar proof/admission state, register initialization, absolute scalar
call relocations, assertion identities and validated entry metadata all matter.
The conservative direct transitive closure is not necessarily required by this
emitter, and does not account for indirect-call dependencies. The 30 ms census
cost includes serialization of every body and is not a proposed cache's cost.

Defer a persistent-cache runtime implementation until the body churn is explained
and a narrower complete key is specified. Keep the real-edit records and current
preparation costs as the decision basis. Do not benchmark unchanged programs to
hide invalidation or infer rlib validity from unchanged public interfaces.
