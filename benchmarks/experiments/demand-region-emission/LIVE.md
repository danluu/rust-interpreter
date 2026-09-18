# Live demand-region integration: next implementation

The region emitter, compact immutable analysis, 16 MiB retained-plan pool and
own-thread append/patch primitive are qualified. Full eager execution remains
the default. Integrate the runtime under one explicit demand-region option,
requiring resumable calls and preserving complete Rust checking.

## Ownership and admission

Initialize a function once. Retain its immutable analysis only if the bounded
pool admits it; otherwise reuse that analysis for ordinary eager emission.
Initialize scalar callees under the existing policy before either path. Allocate
one stable full-function resume table and block table; never move a published
resume table. Its currently missing slots stay zero and use existing VM fallbacks.

Bound extra publication metadata separately (proposed 16 MiB charge), including
function slots, per-PC frontier state, per-region records and pending edges.
Account actual vector capacities. On initial admission refusal, use eager
emission; after partial publication, a region refusal keeps its VM fallback.
Temporary staging is separate from retained ownership. Preserve code and resume
table budgets. Do not reanalyze a function or change native register assignments
when another region is encountered.

Use a constant-time frontier byte per original PC to distinguish unattempted
leaders from nonleaders and already attempted regions. Per-function region
records remain sorted by PC for staging/link lookup. Pending edges belong only
to their source function and a declared successor leader. Prefer a bounded flat
edge arena with per-target linked-list heads over repeatedly copying fan-in
vectors or scanning every edge for every compiled region. Grow retained buffers
with staged replacement ownership when needed, so a failed charge or allocation
does not mutate committed metadata. Resolved slots may remain charged initially.

## Region transaction

Stage one fragment with the current assertion base. Retain its declared branch
sites, local fallbacks and internal entry. Resolve outgoing branches only to
already published internal entries in the same function, or to the fragment's
own internal entry. All other branches initially use their exact VM tails.

For pending incoming edges to the new region, verify ownership, expected old
words and target identity, then construct ordered CodePatch replacements.
Reserve assertion storage and all needed publication/pending-edge capacity before
committing code. On any precommit refusal, leave old code, tables, assertions and
metadata unchanged. After successful append/patch, publish the preallocated
metadata and the stable table slot without any further fallible work.

Count compiled functions and fixed register assignments once per function,
compiled operations once per region, and compilation time without double-counting
nested scalar preparation. Keep diagnostic region declines separate from the
existing whole-function refusal statistic. Preserve enough per-region publication
data (offset/length/internal target/assertion base) for exact later reconstruction.

## VM dispatch

Prepare an unattempted leader before the resumable native lookup. After native
execution returns at an unattempted leader, return to that preparation point
before interpreting its first instruction. A budget/preflight decline at an
already attempted leader must still execute the existing one-instruction VM tail;
never retry it indefinitely. Mid-region PCs and unsupported instructions retain
ordinary interpretation. Instruction exhaustion keeps priority over subsequent
faults/returns. Cover direct/indirect calls, returns and TLS callback entry paths.

Update profiling block-end metadata only when a region is published. Native and
interpreter counts may repartition, but complete original per-PC logical counts,
fault order, result, memory and entropy must agree.

## Diagnostics and qualification

Demand regions can interleave functions in the code arena. Add an explicit map
schema/mode for per-region publication records rather than assuming each function
occupies one contiguous range. Reconstruct every fragment using its saved
assertion base and immutable assignments, resolve its declared successors against
current published entries, and verify every final byte/table entry/assertion.
Do not silently label an eager reconstruction as a demand capture.

Qualify arbitrary emission order, self/back/cross-region edges, unsupported and
declined successors, code/plan/metadata/table limits, stable old entries, recursive
calls, TLS, assertion/fault order and all instruction-budget tails. Run current
workspace/Python/strict-cache controls and exact original profiles before the
unchanged primary-first changed-source screen. Retain the adopted VM as control;
only a passing complete comparison can support adoption.
