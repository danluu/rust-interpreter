# Complete parser function census at the existing limit

The failure-only exporter reports10,009 registered instances,9,995 requiring
bodies,9,893 bodies stored before the current body, one completed current body,
and101 pending bodies. The accounting reconciles exactly. Only14 registrations
are unneeded address-taken placeholders; dropping those would not materially
solve the capacity problem. There are218 address-taken instances,204 required,
58 with unknown ABI shape, and25 indirect-call shapes. These overlapping sets
do not identify the causal cost of indirect reachability.

The10,009 instances cover3,115 definitions. Core contributes5,465, types_nodes
2,178, std445, gram_core427 and alloc404. Frequent instantiations include
NonNull::cast701, Result::branch412, FromResidual407, drop_glue388,
NonNull::as_ptr291 and Node::rep_ptr250. The current body is a gimli reader,
showing backtrace-related code also enters the graph. The stored bodies contain
675,085 bytecode operations; the current body has167. Counts alone do not show
which code executes, which imports are avoidable, or where compilation time goes.

Both diagnostic exporter test profiles pass88 tests. One complete114-entry
parser command produces the expected original expansion failure; native114
proof and all source/assertion bytes are reused and validated. No parser guest
test executes. Full census coverage is verified; no admission or scheduling
rule was changed to obtain it.

Next, qualify a coordinated finite function-count budget of32,768 for lowering,
function-cache read/write and optional per-function observers. Retain their
existing byte bounds. The current10,000 cap also appears in cache serialization,
so changing only the lowering threshold would leave warm compilation broken.
Use a cache round-trip above10,000 and explicit over-limit read/write rejection,
then run the same complete parser target. This is a support-capacity experiment,
not a speedup claim or proof that conservative graph expansion is optimal.
