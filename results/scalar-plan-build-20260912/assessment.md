# Certified scalar-plan reuse: parked

Retaining the certified scalar frame layout removes the duplicate scalar MIR
visitor and planner in aggregate capture while preserving exact slot/extent
checks, bounded fallbacks and aggregate relocation verification. The candidate
passes371 Rust tests in each profile, with one existing ignored test. All six
completed public workflow histories preserve corresponding bytecode and original
assertions, including deliberately wrong production edits and fresh restoration.

| Complete histories | Edited pairs | Median paired build-wall change | Median paired build-CPU change |
|---|---:|---:|---:|
| fre token01/02/04 |15|-1.986%|-1.132%|
| pgrust01/02/03 |15|+0.256%|+0.341%|

The5% primary build-wall gate was missed. All individual history and pgrust
regression guards passed. Park the compiler change; no Ruff/Nushell promotion
run or unchanged-binary performance retry follows. These shared-host values
are descriptive build-readiness measurements, not confidence intervals or a
cold-build, whole-command, runtime, general or unknown-holdout speedup claim.

Both arms use the same frozen VM and wrapper, ordinary checking, source pins,
explicit limits/settings, common instrumentation and distinct actual Cargo
caches. Persistent function-payload reuse remains disabled. Three independently
initialized histories rotate the initial mode order; all15 edited pairs per
project enter the fixed median-of-paired-ratios decision. No A/A value is
subtracted. Exact tools, source snapshots, tests and controller hashes appear in
[qualification.json](qualification.json); ratios are in [measurement.json](measurement.json).

Token03 stopped before its third edit's Cargo-check control because free space
fell to1,047,363,584 bytes, below the1GiB floor. Its15 primary commands, four
checking controls, ten retained artifacts and three completed edit pairs remain
as [interrupted evidence](interrupted-token03/records.json). Source restoration
succeeded, but that history has no final restored-original build/execution.
Before inspecting a performance decision, a fixed [recovery plan](recovery-plan.md)
replaced this incomplete history with fresh token04 using the same third order
and unchanged settings, then ran the unstarted pgrust03. Partial pairs are
reported separately and never spliced into the complete-history gate.

Only8,649 non-executable object files from three completed task-owned native
caches were reclaimed under the shared lock. Exact before/after inventories,
identity checks and re-verification preserve all other cache files, immutable
binaries, source snapshots, raw receipts and executed bytecode. The1.195GB logical
object sum is not physical space reclaimed on the shared APFS host. No unrelated
worktree/cache or process was changed. Later free-space growth preceded this
reclamation and is not attributed to it.

The implementation, exact patch and immutable binary remain available on the
parked experiment branch and under task-owned `.work/build-general-20260912`.
The next distinct candidate additionally reuses initialized local types and
pre-planner scalar eligibility; it needs its own qualification.
