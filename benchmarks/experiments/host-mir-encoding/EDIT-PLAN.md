# Host dependency MIR: prospective edited-command comparison

Candidate466c60a2 differs from integrated baseline49746a22 only in its wrapper.
Sixteen routing tests per profile,19 process checks and20 real Cargo/command
checks pass. The same library was compiled as both host and guest, used by a
build script and proc macro, and edited. All original/wrong/restored outcomes
and four bytecode/catalog pairs match. Uncalled type and borrow errors are
rejected before execution. No recorder enters this performance comparison.

Run Nushell type-relations first: fourteen original tests, three complete
histories with five cumulative production edits, original/wrong controls and
compiled restoration. Use baseline, independently cached identical duplicate,
and candidate, plus ordinary native, line-tables native and Cargo check.
All six routes use two Cargo workers; custom uses two prepared workers and
the same strict exporter, VM, std-MIR and runtime limits. Native uses default
libtest concurrency. Function reuse is automatic on all custom routes.
Limits per guest are100 billion logical instructions,150,000 allocations,
64MiB working memory and4,096 frames, verified from the effective VM report.

The six custom orders are012,120,201,210,102,021, repeated across the fifteen
edited states. Each custom mode occupies each position five times. Original
and wrong states are scheduled separately. Native/line-tables alternate order
and alternate before/after the custom group; check is last. Each mode owns a
fresh target/cache namespace and sees every state. Require132 commands, all
fifteen edited pairs and fifteen A/A pairs. Hash all measured inputs and retain
every command, source transition, executed artifact, catalog and Cargo timing
report. All three custom artifacts/catalogs must agree within each source state.

For this wrapper component, retain it as a measured improvement only if Nushell
median paired wall gain exceeds its observed A/A wall envelope and paired CPU
does not increase. A/A is the maximum absolute per-edit median ratio deviation
across the three cycles, with at most4% wall and3% CPU. It is descriptive noise,
not a confidence interval. There is no separate8% component threshold. The
previous runtime composition gates remain unchanged. No subtraction of noise,
discarded pairs or retiming an unchanged candidate to obtain a pass.

Run the same full pgrust guard after Nushell even if the primary fails. Require
at most5% paired wall/CPU regression and the same noise bounds. Only a passing
Nushell/pgrust result permits the more expensive Ruff confirmation with six
original tests and the same132-command protocol and5% guards. Adoption requires
all three; a failure preserves the candidate without retiming or default change.

Initial empty-target builds are single setup observations, reported separately
from edited medians, not repeatable cold-speed estimates. Retain both native
controls and rounded libtest duration; the remaining time is not pure codegen
or linking. Cargo --timings is enabled on every route for unit-level attribution.
No checking or dependency is omitted based on runtime reachability.

Use the owning workspace's benchmark lock with45-second admission. Each case's
admission requires six times its prior measured native target bytes with20%
growth, plus8GiB; every child retains an8GiB free-space floor. Check actual
storage before any source edit. Do not alter unrelated work, private caches,
held targets, installed binaries or source snapshots used by another process.
No additional storage cleanup is scheduled. Unexpected outcome, provenance,
admission or disk failure stops the controller and preserves its completed work.
