# Current state — September 13, 2026

Manual optimization continues indefinitely. The saved goal remains paused.
The task is a general custom Rust interpreter/direct AArch64 JIT, guided by
real changed-source build/test commands across small and large projects.
Private repository: `danluu/rust-interpreter`. Qualified changes go to main.

The guarded-range runtime is adopted on main (`4dcc889`). It validates one bounded
related-pointer range at native-region entry, reuses its translated base, and
falls back to the original ordered path if the stronger guard fails. Rust type
and borrow checking still finish before guest execution. No external guest
backend, project-specific shim or lazy unchecked execution is introduced.

All 726 performance commands and five gates pass. Token improves wall 2.55%
and CPU 1.43% against the prior custom runtime; the wall pass is narrow against
2.275% observed A/A. Its command remains 1.773 times ordinary native. Folded
matching, pgrust hashfn, private rg-aot and Nushell type-relations pass regression
guards without established incremental gains. The pgrust guard covers four
hashfn tests and the Nushell guard covers 14 tests. Do not generalize those
selections into complete database or shell coverage.

[Complete comparison](results/guarded-ranges-admission-resume-01/assessment.md).
All sources restore, 8,999 case inputs verify, and no completed case was repeated.
The earlier lock/disk admissions and offline profile-validator repair remain
recorded. Historical failed candidates keep their original decisions.

The complete tool `c743a75d` preserves exact VM `4e9c9af6`, current exporter
`cccdc909` and wrapper `10fb7656`. Source-bound Rust/profile proofs are reused;
132 harness checks and 263 fresh strict cache/Cargo/project commands pass.
Every real-project artifact, catalog and assertion outcome matches the retained
history. Main's compiler observers/query reuse and validator fixes are preserved.
Borrow-check reuse remains off by default; execution options remain explicit.
[Integration](results/guarded-ranges-main-qualification-01/assessment.md).

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
The actual-emitter local-value census is a separate next optimization candidate.
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
