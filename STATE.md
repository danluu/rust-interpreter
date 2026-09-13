# Current state — September 13, 2026

Manual optimization continues indefinitely. The saved goal remains paused.
The task is a general custom Rust interpreter/direct AArch64 JIT, guided by
real changed-source build/test commands across small and large projects.
Private repository: `danluu/rust-interpreter`. Qualified changes go to main.

The guarded-range runtime is qualified for adoption. It validates one bounded
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

Next: publish the qualified runtime, then probe the full original pgrust
SQL-parser library target before declaring new edit timings. Static source
inspection finds 113 parser tests and one tree-parity test; actual native
inventory and custom support remain unverified. Preserve pgrust's profile
choices and use matched incremental settings for any later warm comparison.
The actual-emitter local-value census is a separate next optimization candidate.
Verify the possible automatic tool-source fingerprint omission before fixing it.

Every latest suggestion has an [explicit disposition](docs/SUGGESTIONS-REVIEW-20260912-2210.md).
`suggestions.txt` remains user-owned, unmodified and untracked. Update short
current-state notes at milestones; detailed receipts belong in results.
[Prior state snapshot](docs/history/STATE-20260913-before-guarded-integration.md).

Keep the shared benchmark lock, 45-second admission, two Cargo workers,
conservative cache estimates and an 8 GiB per-command floor. Read the independent
disk sampler; do not start another cleaner or repair it. Preserve all other
sessions and processes. No subagents, AWS activations or billing fallbacks.
[Next work](RUNTIME-NEXT.md).
