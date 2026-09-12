# Reuse owned compiler data and stable liveness transfers

Prospective plan written before candidate integration, build, or timing. This
candidate extends the parked local-analysis compiler de1df7f with owned leaf
inlining eb4d2f25, consuming coverage ranges e846f082, and stable block liveness
transfer reuse 5f8c5714. The preceding complete screen measured token build wall
-3.629076% and CPU -4.684199%, missing the fixed 5% wall gate. It is retained as
a failed candidate; the next measurements use a distinct binary and new targets.

The leaf-inline worker retains the original graph until replacement selection
finishes, preserving budget, validation, rollback, and reporting. Coverage owns
its already-private input collections; ordering, checks, and certificates remain
unchanged. Liveness reuses only an evaluated transfer with identical successor
union and charges the exact original logical work, including every fallback
budget. Original algorithms/reference oracles remain in correctness tests.

Baseline remains frozen tool851ddd5f33e18954b586ec081af021778407efddf843afdaae88ec1f6647c527.
The candidate bundle will use the frozen baseline VM and wrapper for both timing
arms, recording built and selected binary provenance separately if Rust library
linkage changes the candidate-built VM hash. No new runtime VM is under test.
Qualify the release exporter against that VM with the full differential suite,
and run debug/release workspace tests before timing. Freeze all source inputs.
No profile, common launcher, metric, guest options, test selection, comparison
VM, toolchain, standard MIR, or fixed gate change is planned.

Next run prefix: owned-analysis-{token,pgrust}-20260912-{01,02,03}.
Use all six planned histories and the prior fixed protocol below; no unchanged
candidate retiming for a pass, no selecting or subtracting noisy observations.
Three GiB history admission and one GiB per-command floor remain unchanged.
The candidate must pass required public confirmations before production merge.

--- Prior fixed protocol and controls (inherited) ---

# Reuse local lowering analyses: distinct composed build candidate

Fixed before this candidate's build or timing. Baseline remains compiler source
c1c3b3a, tool851ddd5f33e18954b586ec081af021778407efddf843afdaae88ec1f6647c527,
with published common controls17c555b; later upstream8e81387 changes storage
scripts/reports only. Freeze source/tool manifests again before timing.

Scalar certificate reuse alone was parked after its fixed gate: token median
paired build wall-1.986%, CPU-1.132%, pgrust approximately flat. Preserve that
complete failed screen and its storage interruption; do not retime that binary.
This distinct candidate composes the certificate with initialized local Ty/shape
reuse (8fa5c0f), pre-planner visitor eligibility reuse (9c27c88), and fixture
provenance correctionb767335. All three source analyses remain scoped to one
immutable MIR body/Instance; no persistent payload schema, checking policy,
planner/promotion algorithm, runtime, or generated-bytecode change is intended.

Type/layout initialization preserves original validation/allocation order. Move
shapes into the existing certificate without a second long-lived shape copy.
Projected types retain original normalization. Synthetic Lower::empty paths
retain fallback normalization and visitor analysis. Keep eligibility before
planner entry-zero liveness changes it, even on bounded/no-improvement plans;
keep promotion's direct aggregate/call operand exclusions and code/local bounds.

Qualify debug and release workspace tests plus full native/interpreter/JIT
fixture validation with the installed candidate tools; explicitly run the new
261-input standalone local-layout oracle test. Record111 native-oracle inputs
through both engines in that fixture as part of the larger validation. Baseline
and candidate VM/wrapper hashes must match. Common83Python checks already passed
and remain unchanged; run relevant validation if common code changes.

Performance uses the SAME exact shared settings and cases as the prior scalar
screen, with three independently initialized one-cycle histories per project
and initial orders native/baseline/candidate, baseline/candidate/native,
candidate/native/baseline. New run IDs/namespaces and empty targets. Use all15
edited pairs/project; record all anchors, wrong production assertion failures,
checking references and freshly rebuilt/executed restored original states.
Require exact paired artifact identity. Fixed token gate: >=5% median paired
build-to-ready wall improvement and improving paired build CPU. Require <=5%
wall/CPU regression in every history and aggregate pgrust. No A/A subtraction,
favorable early stopping, or selecting histories from measured results.

All planned histories run unless infrastructure/correctness controls fail. A
storage-aborted history is retained separately; only a pre-recorded fresh full
replacement of the same order/settings can restore a missing complete history.
No performance-rejected unchanged binary is retried for a pass.

A passing screen retains the original Ruff and Nushell generic-interface
confirmations with <=5% wall/CPU regression guards. Do not admit them without
sufficient space: historical estimates are7.34GiB for Ruff and14.82GiB for Nu,
not guaranteed bounds for current settings. Preserve candidates pending required
qualification when capacity is unavailable; continue independent source work.
No unknown-holdout, cold-build or full-command performance claim follows from
build-readiness timing alone. Scalar pass timing now excludes initialization
shape collection, so nested phase time is diagnostic, not the primary metric.

All builds/tests/benchmark/cache work uses the shared lock and task-owned paths.
Preserve immutable binaries, executed artifacts, source snapshots and raw logs.
Only disposable caches from explicitly completed owned runs may be reclaimed
with exact evidence/identity/open-file checks; do this between timed histories.
No user-owned workload/cache/source is modified or signaled, and no AWS offering
is activated or purchased. Require at least3GiB free at history admission and
retain the1GiB per-command floor; record capacity changes and interruptions.
