# Compose native indirect transitions with the adopted scalar runtime

Base693b4dc3 restores bytecode source exactly from main693f9ae1, whose runtime
is adopted tool df4006e0 / VM6ac4dd9e. The aggregate experiment remains archived
and parked. Rebase only the qualified indirect transition delta70b09b03..5ffb948c;
retain current scalar Calls, scratch memory reuse, descriptor support, strict
validation and current source/metadata observers. No successor-flush change.
Earlier indirect candidates used baseline35df4077, not this composition. Preserve
both failed screens; do not add their estimates or relax the original gate.

Append immutable indirect metadata to the resumable cursor after scalar profile
metadata, preserving existing offsets. Handle full128-bit function values,
exact argument/result signatures, stable host entry tables, cold/unsupported
fallbacks, limits, zeroing, ordered aliased arguments and fault order as before.
Reject partial-validation artifacts for indirect execution, independently of
whether scalar Calls are enabled. Both options remain explicit and immutable
for a prepared owner. Guest compilation uses only our direct AArch64 emitter.

First run the carried eight indirect fixtures with scalar mode independently
on/off and persistent registers on/off, three metadata controls, and two new
composition fixtures with warm polymorphic indirect targets calling scalar
children, every instruction tail, exact original-PC profiles, preparation-option
changes and partial-artifact rejection. Then whole bytecode/workspace checks in
both profiles, all Python contracts,122 strict/cache commands and original
profiles/reconstruction with the exact compiler/exporter/wrapper unchanged.
Disabled-indirect emission must reconstruct the adopted code before timing.

Only fully qualified immutable tools may enter the original40-command full-token
changed-source primary (12 unchanged original tests, five valid production edits,
negative edit, restore, A/A duplicate, historical anchor and ordinary native).
Use normal entropy, two Cargo workers and two prepared workers. Existing wall
and CPU gates remain unchanged. If it passes, predeclare full histories and all
five project plus both full-parser guards before running; otherwise park it.
No unchanged-build performance measure or unchecked guest execution.

Hold the shared lock with45-second admission. Use only ROOT's shared target,
two Cargo/test workers, max(14 GiB,8 GiB+twice allocated target) build admission,
12 GiB analyses and8 GiB child floor. Setup and compilation time are separate
from benchmark observations. Preserve all other sessions, all failed commands,
and the paused goal. No subagents or model/billing fallbacks.

The initial debug run's option-message assertion failure is closed. The second
passes10 integration,3 metadata and355 library tests in each profile (15 ignored).
Before full build, a third focus adds3 full-memory controls/profile, using the
previous independent test-only Drop observer. Compare complete active linear
and heap bytes even on errors, warm prepared targets, before/after-write faults,
readonly/null/overflow/padding addresses, budgets and resource tails. Observer
changes are cfg(test) only and do not alter guest execution.
