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
