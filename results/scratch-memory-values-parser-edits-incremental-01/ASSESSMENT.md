# Matched incremental parser guard passed; no speedup demonstrated

All 88 commands preserve the 114 original assertions, expected incorrect-edit
failures, candidate/control artifact identity within each cycle/state and source
restoration. Median paired candidate/baseline wall is **1.005451**, CPU
**1.005560**. A/A envelopes are 0.022901 wall and 0.023070 CPU. The predeclared
regression margins pass at **1.028352** wall and **1.028630** CPU.

The roughly 0.55% measured increase is within control variation. This does not
establish a parser speedup. Candidate/native is **1.263277** wall and **1.283758**
CPU, so the full parser remains a losing row against native. Token/folded gains
must not be generalized to this workload.

Every arm uses CARGO_INCREMENTAL=1, two Cargo workers and the original profiles,
with fresh independent compiler namespaces. Candidate alone enables scalar Calls;
all custom arms share the qualified compiler. Cross-cycle compiler identities
are retained, not normalized. The repository-default parser guard and Nushell
full guard remain before adoption.
