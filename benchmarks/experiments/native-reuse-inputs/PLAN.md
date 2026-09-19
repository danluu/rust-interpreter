# Necessary inputs for native reuse across real edits

The closed preparation-cost audit must precede execution of this study. It
shows material remaining compilation intervals for fre and the full parser,
with much smaller absolute costs for pgrust/private/type-relation workflows.
PreparedJit already retains native code inside each worker; do not implement
that mechanism again. This study executes no guest and publishes no native code.

Read the retained adopted-baseline bytecode snapshots from the complete original,
wrong-edit, valid-edit and restored histories used by the cost audit. Deduplicate
only identical SHA256 payloads. Preserve all chronological transitions in the
analysis, including wrong-test edits, anchors and reverts. Include all five
projects, the incremental parser and recent token primary; keep private names
out of published output. Full checking in the original exporter and structural
bytecode validation remain prerequisites; partial-validation artifacts decline.

Compute a local identity from every serialized Function field, including name,
register count, frame layout, argument/result slots and all operations. Keep its
numeric function ID explicit. A second necessary-input identity additionally
binds every directly called Function's complete identity, sorted by callee ID.
This catches ordinary Call frame/zeroing assumptions and the possible scalar
leaf implementation. Current scalar memory_plan rejects any callee with Calls;
do not generalize that fact to a future recursive/inlining backend.

Use a conservative program namespace containing format version, target, function
count, readonly data, mutable-static initializers, TLS layout and the exact
adopted uses_heap decision. Report namespace invalidation independently from
local-body and direct-callee invalidation. Do not normalize numeric IDs, reorder
functions or omit a consumed input just to improve the reported reuse fraction.
An unchanged local body is not evidence that a native template is reusable.

Controls must cover body edits/reverts, unchanged unrelated functions, callee
body and ABI/initialization changes, global heap-mode and initialization changes,
numeric-ID changes, streaming hash equivalence and bounded rejection. Use the
existing bincode representation and SHA256 with explicit diagnostic domains.
Bound artifact size, function/op counts, manifest count and accumulated output;
process one artifact at a time. Record standalone validation/keying work only as
diagnostic preparation cost, not a real cache hit or end-to-end measurement.

These keys are necessary-condition diagnostics, NOT a production cache format
or a proof of safe native loading. Any later cache still needs exact handling of
scalar target relocations, assertion IDs, current scalar admission, compiler
analysis budgets, remaining arena capacity, entry/resume tables, metadata and
format/VM/options identity, corruption, interrupted publication and bounded
storage. Current sparse original profiles may provide explicitly scoped compiled
body weights only when their artifact SHA matches; otherwise report unweighted
counts and bytecode sizes without inferring hot hit rates.

Keep production runtime/Cargo sources adopted. A standalone integration test
module is sufficient for this offline observer; no guest backend, compiler
wrapper or frontend change is needed. Build/test admission is
max(14GiB,8GiB+2*allocated shared target), two workers, root benchmark lock with
45second wait,8GiB child floor. Never compete with or control peer builds.
Freeze source and exact input evidence before running. Preserve completed work
if later closure admission fails. No new timing or production cache is admitted
by this plan alone.
