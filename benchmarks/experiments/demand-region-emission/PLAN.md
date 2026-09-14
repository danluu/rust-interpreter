# Demand-region prototype: extract reusable function analysis

Start from adopted runtime source after the closed demand-region census. Keep
full-function emission and all runtime options unchanged in this first step.
Move register read bounds, persistent liveness/assignments, local-fill hints,
call-slot hints and native region leaders into one immutable analysis object.
Preserve analysis order, limits, test switches and the existing body-emission
loop. Do not yet retain plans across calls, compile a subset, patch live code,
change admission or claim a preparation improvement.

Qualify all bytecode library controls in debug/release and reconstruct both
closed unprofiled adopted captures byte-for-byte, including scalar call targets,
assertion identities and operation maps. The existing saved-memory observer
publishes no code. Bind all sources, artifacts, controls and terminal receipts;
use the shared target only from ROOT, two workers and conservative disk checks.

Only after equivalence passes, separate single-region emission and model pending
edges/publication transactions before executable patching. Future retained plans
need explicit aggregate memory/work bounds and stable per-function assignments;
fault, budget and code-capacity refusal must leave a safe VM path. No production
adoption or changed-source screen follows from this refactor alone.
