# Current state — September 13, 2026

Manual optimization continues indefinitely. The saved goal remains paused.
The task is a general custom Rust interpreter/direct AArch64 JIT, guided by
real changed-source build/test commands across small and large projects.
Private repository: `danluu/rust-interpreter`. Qualified changes go to main.

The guarded local-value/scalar-Copy runtime is adopted with the current compiler.
It preserves proven frame-disjoint facts across writes and folds existing local
scalar-copy addresses, retaining ordered fallback and memory fault semantics.
Rust type and borrow checking still finish before guest execution. The custom
interpreter/direct AArch64 JIT remains the guest backend; the16 MiB default stays.

All726 changed-source performance commands and five gates pass. The primary
improves4.73% wall/3.83% CPU against the previous custom runtime and remains1.641
times ordinary native. Folded matching, pgrust hashfn, private rg-aot and Nushell
type-relations pass regression guards. Nushell's incremental difference stays
inside variation. These selections cover four pgrust hash tests and14 Nushell
tests; they do not establish complete database/shell coverage.
[Complete comparison](results/guarded-local-facts-full-continuation-01/assessment.md).

Qualified complete tool `35df4077` retains exact measured VM `f0e5f2ea` and uses
new exporter `cf4b3499`/wrapper `45bca4f2`. It passes513 workspace Rust tests per
profile,130 internal remapping controls,119 strict/cache/Cargo commands,40 exact
project histories and all114 original parser tests. The final audit verifies
9,639 unique frozen inputs and579 Git source bindings. The publication merge
also passes334 Python contracts (16 declared skips) and preserves the other
session's owned-compiler loader improvement. Timing ratios stay bound to the
original measured compiler binaries; these integration checks establish
compatibility without repeating the timing campaign.
[Integration](results/guarded-local-facts-main-final-audit-01/assessment.md).

The local-value-transfer observer reconstructs all three current code/maps exactly
but saves only8 /8 /0 static bytes and1,792 /8 /0 weighted forwarded accesses.
Park it without timing; its test-only implementation remains experimental.
Two new owned native-PC captures now identify native Call/Return code at26.23%
/34.68% of attributed generated samples, plus8.18% /12.51% register flushing.
Next partition the actual protocol emission and label those already captured
PCs; preserve all guards before choosing a mechanism. These partial perturbed
samples are diagnostic, and native calls are not VM exits.
[Current samples](results/adopted-runtime-sampling-01/assessment.md),
[eviction-loss result](results/local-value-transfer-census-01/assessment.md).

The general boxed `FnOnce` receiver fix is qualified:88 exporter tests per
profile,18 focused guest tests across interpreter/JIT modes and78 existing
dynamic/closure/cache/strict Cargo commands pass. Tool `15574904` retains the
exact adopted VM and wrapper. Sized dynamic bytecode matches the prior control.
[Receiver fix](results/boxed-fnonce-after-01/assessment.md).
The full original pgrust SQL-parser target now passes all 114 native and custom
JIT tests, including C reference vectors. General function-capacity, environment
read and checked C-string support remove the subsequent blockers. The combined
main compiler qualification and publication audit pass. All 40 existing-project history
commands now preserve exact artifacts and assertion outcomes. The workspace
passes 484 tests per profile, the final exporter passes
89 per profile, and 119 focused/cache/strict Cargo commands pass. All 4,918 parser
inputs verify; source and assertions are unchanged.
[Complete parser support](results/pgrust-parser-support-04/assessment.md).
The complete 66-command default-profile parser comparison now passes its
correctness controls but is 15.78% slower than native on edited wall time
(8.29% more child CPU). The separately completed matched-incremental comparison
is23.03% slower wall and24.02% more CPU across15 edited pairs. Its revised
protocol retains the failed22-command cross-cycle study and runs only44
unstarted commands. Paired allocation traces with function reuse disabled locate
the original/restored layout difference in rustc's sharing of an immutable
literal, before exporter placement. A/B artifact identity holds within each
cycle/state. All114 native/custom assertion outcomes match and sources restore.
The dominant reference-vector test spends94.13% of its interpreted operations
in one large parser routine. Offline emission produces16,554,488 native bytes
for that routine alone, establishing whole-function capacity pressure.
The completed explicit 16/32 MiB screen retains the 16 MiB default and parks the
larger treatment: its 0.69% paired wall improvement is inside 4.04% A/A variation.
All 32 controls agree with native, including the wrong edit. Five commands were
retained after a failed-test statistics validator repair; exactly 27 new commands
completed the schedule. No valid edited timing preceded the repair. The large
routine reaches 66.60% of its bytecode and already avoids bulk register zeroing.
No unchanged full capacity study or broad lazy-region rewrite follows this
result. Return to actual-emitter local-value forwarding composition evidence.
[Capacity screen](results/parser-jit-capacity-screen-continuation-01/assessment.md).
[Parser baseline](results/pgrust-parser-edits-repository-continuation-01/assessment.md).
[Matched incremental](results/pgrust-parser-edits-incremental-history-01/assessment.md).
[Combined compatibility](results/environment-main-final-audit-01/assessment.md).
The actual-emitter local-value censuses are complete. All three public baselines
reconstruct exactly. Composition `317a0bf1` of guarded local-value retention,
preserved static facts and scalar-copy address folding now passes 504 workspace
tests per profile, 119 strict/cache controls and three exact real-test profiles.
Both reduced operation spans and increased flush code remain reported; the
profiled emitted sizes match the independent census. Earlier fixture-setup and
admission failures remain recorded. The 40-command token screen now passes:
paired wall is 7.91% lower and CPU 6.19% lower, with A/A envelopes 5.002% and
3.814%; the command remains 1.727 times native. A workspace-library parser repair
retains one completed native control and executes only 39 new commands. All 13
additional real controls, 21 full-protocol checks and all114 original parser
tests pass. Four full histories now pass594 commands: token improves wall4.73%
and CPU3.83% (A/A1.714%/1.583%), while folded, pgrust and private rg-aot pass
regression guards. Token remains1.641 times native. Nushell now also passes its
132-command guard: paired wall1.00115, CPU0.99711, with wall/CPU noise margins
1.04160/1.00547 within1.05. The complete726-command audit verifies9,005 inputs,
all source restoration and retained artifacts. Continuation01 retained594
commands and ran132 new ones, with zero repeats. Earlier disk/lock refusals and
verified compiler-cache retirement remain recorded. Proceed with current-main
compiler integration and compatibility qualification; these timing ratios remain
bound to the measured exporter/wrapper. Private details remain local.
[Complete decision](results/guarded-local-facts-full-continuation-01/assessment.md).
[Composition evidence](results/guarded-local-facts-composed-census-01/assessment.md),
[qualification](results/guarded-local-facts-profile-01/assessment.md).
The automatic tool cache now includes its selected toolchain identifier: the
retained regression fails before the fix, and 123 runnable root tests pass after
it (10 existing skips). Explicit immutable keys remain usable. The unrelated
archived backend crates correctly remain excluded.
[Cache fix](results/toolchain-cache-after-01/assessment.md).

Every latest suggestion has an [explicit disposition](docs/SUGGESTIONS-REVIEW-20260912-2210.md).
`suggestions.txt` remains user-owned, unmodified and untracked. Update short
current-state notes at milestones; detailed receipts belong in results.
[Prior state snapshot](docs/history/STATE-20260913-before-guarded-integration.md).

Keep the shared benchmark lock, 45-second admission, two Cargo workers,
conservative cache estimates and an 8 GiB per-command floor. Read the independent
disk sampler; do not start another cleaner or repair it. Preserve all other
sessions and processes. No subagents, AWS activations or billing fallbacks.
[Next work](RUNTIME-NEXT.md).
