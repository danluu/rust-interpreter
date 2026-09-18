# Share identical cold fault tails within a native function

The rejected composition remains parked. Start with saved native code from the
two closed current-host adopted-runtime captures. The new hypothesis is code
footprint: ordinary regions repeatedly emit identical complete fault returns,
including status materialization, memory/budget publication and host restoration.
Share only complete byte-identical `fault_tail` spans inside one function.
Keep a one-word local branch at each duplicate tail; existing conditional fault
edges still target that local label. No hot memory checks or guest work change.

First run a bounded offline census. Match the exact adopted nine-word return
suffix and status materialization; reject other shapes, interior control flow,
nonterminal tails, short bodies and cross-function sharing. Count each original
tail once. A duplicate may branch only to an earlier retained identical tail
within AArch64 B's signed 26-word-bit displacement. Keep every other map span,
scalar body, transition and failure outcome outside this proposed change.
Require complete same-process byte/map/sample identities and exact generated
sample accounting. Report code bytes and affected function sample context, not
cycles saved or projected speedup. The census publishes no executable code.

If scope is material, implement the bounded interning in the custom emitter on
the adopted Rust source, with safe no-sharing fallback when a limit is reached.
Qualify actual native fault status, assertion identities, every budget prefix,
callee-saved state, entries, branch reach and code maps. Keep each retained tail's
fault ownership; no shared assertion/budget/successor tail or epilogue-suffix
sharing in this candidate. No decoder-based rewrite of published machine code.

Only full correctness, strict-checking and exact original workload controls admit
a fresh 40-command changed-source primary. Keep all existing A/A and CPU gates;
failure stops the candidate. A pass permits full project and parser guards.
No extra independent personas/agents, repeated unchanged timing or other backend.

Use the root benchmark lock with 45-second admission. Offline admission12GiB,
child floor8GiB; future builds reserve max(14GiB,8GiB+2*shared-target allocation),
two Cargo/test workers and only the existing root-owned target. Preserve the
paused goal, all peer sessions, private caches and completed evidence.
