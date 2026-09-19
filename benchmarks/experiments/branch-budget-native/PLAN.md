# Isolated typed/native branch reservation prototype

Base: adopted bytecode crate fca687eb, with no parked compact-switch code.
Closed branch-budget-reservation-01 supplies the diagnostic scope and14-control
abstract model. Build feature `branch-budget-reservation` defaults off. Keep the
installed df4006e0 runtime and unchanged exporter/wrapper for comparison.

Stage1: implement bounded typed region discovery and credit certificates. Keep
the exact native predicate, starts and1024-op splits. Validate shape/edge limits
before consuming the existing range-analysis budget; compute each range plan
once in original order and retain it for emission. Guarded destinations, calls,
backedges and unsupported gaps cut fast edges. Credit<=4096, refunds<=4095.

Stage2: checked entries guard/debit credit; fast entries start after that debit
and before profile accounting. Add source-aware edge metadata without changing
Call/Return links. Refund edge differences using non-flag-setting ADDx22 and
bounded branch thunks. Refund complete pending suffixes in memory/arithmetic/
assertion fault tails and VM successor fallbacks. Budget/range-preflight failure
tails refund nothing. All source states and native entries must be internally
certified before publication; no guest value supplies a host code pointer.

Stage3: native controls exercise unequal paths, mixed forward/backward edges,
all budgets and entry points, every early error, guarded memory, calls, unsupported
operations, code-capacity refusal, ABI canaries and exact cursor/extent commits.
Inspect independent AArch64 encodings; preserve an explicitly disabled emission
reference. Add a distinct operation-map kind for edge thunks and qualify a new
reader rather than modifying historical frozen observer sources. Reconstruct
candidate maps exactly. Full workspace/strict/original-suite qualification and
the preregistered real changed-source primary precede any full guard campaign.

No build is admitted below max(14GiB,8GiB+twice allocated shared target), and that
target is never cleaned. Reclaim only explicitly inventoried owned closed public
evidence/caches with original bytes, metadata, open-file and proof checks.
Shared lock45s, two Cargo/test workers; preserve the other session and paused goal.
Neither this plan nor an unbuilt source commit is a correctness or speed claim.
