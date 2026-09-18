# Diagnostic scalar leaves with checked external reads

The typed current-call join finds 84 block-test transition samples on functions
first rejected for unknown reads. That reason does not prove the rest of a
function is read-only. Add a complete diagnostic plan before native execution.

Introduce a test-only read-only proof mode and explicit scalar Read node. Permit
bounded unknown reads up to 16 bytes, but require every write to resolve inside
the callee frame. Unknown effects, nested calls, unbounded extents, out-of-frame
locals and existing shape/control-flow/work limits remain rejected. Virtual
local bytes start with exact VM zeros. Reads remain live roots even when unused;
their values participate in normal scalar dependencies and original-PC order.

Reference evaluation uses an explicit checked immutable-memory callback. A
future native transaction must exclude the complete fresh callee range,
including alignment padding, from each external read, preserve address-width
semantics, and replay the ordinary Call on any private failure before commit.
Local reads/writes stay in the value graph. No original memory is changed by
the private evaluation. The native emitter explicitly rejects Read nodes; no
production option or admission rule enables this diagnostic mode.

Six new controls compare widths, Copy, padding, chained pointers, CFG joins,
dead-read faults and budgets with the reference interpreter. They also exercise
external-effect rejection, resource limits and fresh-range replay (282 new
reference executions per profile). Rerun the 13 existing proof and five scalar
IR controls in both profiles. Eight recorded commands: six suites, one pinned
artifact census, one join to current sample PCs. No original-project guest runs
and no native code is published. Existing scalar tests add their own synthetic
reference evaluations beyond the 282 new cases.

Scan all functions under the existing 256-million proof budget and 250,000
per-function scalar bound. Count only complete plans with at least one Read,
then join both current transitions and body samples. These are partial perturbed
coverage observations; native bounds checks, preparation, code capacity and
latency benefit remain unmeasured. Implement native support only if warranted.

Use the ROOT-only shared target, two Cargo workers, the global lock and existing
host profiles. Initial admission is max(14 GiB, 8 GiB plus twice allocated
target); retain the 8 GiB child floor and all failed attempts. Do not touch peer
work, cleaner, installed tools or goal state.
