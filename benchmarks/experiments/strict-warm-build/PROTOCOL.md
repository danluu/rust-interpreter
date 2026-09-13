# Strict warm builds below 0.5 seconds

Status: prospective protocol, 2026-09-13. No result is claimed here. The user
has authorized new benchmarks for optimization; the earlier restriction applied
only to the initial report. Changes must work without application source or
manifest changes and must generalize beyond the development corpus.

## What counts as success

The primary workload is the pinned Nushell `type-relations` workflow in
`scripts/workflow_cases.py`: package `nu-protocol`, all fourteen original tests,
and all five cumulative production-body edits. The ordinary Nushell parser
workflow and the rest of `benchmarks/workflow-corpus.json` are regression
controls. Existing interface-edit cases provide broader invalidation controls.
Do not silently replace this target with a smaller package, selected function,
unchanged command, or new microbenchmark.

The target is **strict readiness below 0.500 seconds after a real edit**, with
the whole requested revision validated before it can execute. Measure elapsed
wall time from immediately before the user-facing launcher process starts until
that boundary. Include launcher startup, configuration/tool lookup, Cargo graph
and fingerprint work, scheduling, every required host and target compiler job,
build scripts and proc macros, dependency validation, diagnostics, lowering,
artifact publication, native binding checks, and required VM/backend preflight.
Include waits for workers or locks encountered by that command. Exclude only
the benchmark's admission wait before invoking the user command.

`scripts/interpreter.py` currently records `build_to_ready_seconds` before VM
startup, decoding and validation. Preserve that nested metric for comparisons,
but it alone does not establish this stricter readiness boundary. Until an
instrumented, tested boundary covers all required preflight, use the **complete
successful command through execution of the original tests** as a conservative
upper bound. Never subtract measured or estimated execution from a total to
manufacture a passing build time. Also report complete-command time after a
proper earlier readiness boundary exists.

A qualifying result needs the Nushell latency gate and fresh-project evidence
that the mechanism is correct and its benefit generalizes. The absolute 0.5 s
target applies to Nushell; holdouts test improvement and regressions at their
actual sizes. Independently qualified improvements can land before the target
is reached. No universal latency guarantee for other projects or arbitrary
layout, macro, feature or toolchain changes follows from this campaign.

## Work and source integrity

Benchmark mutations occur only in owned snapshots of pinned revisions. Keep
application manifests, dependency versions, features, required Cargo units,
original tests, assertions, data sizes and iteration counts fixed within a
comparison. Preserve the selected build's normal checking of uncalled bodies,
warnings and lint expectations. Preserve host/target and feature distinctions;
same crate names do not make artifacts interchangeable. Do not replace normal
dependencies with benchmark stubs or factor Nushell into smaller crates.

Reuse requires a documented dependency and environment contract covering every
input the normal build observes. A public-signature hash, timestamp or profiled
call set is insufficient. No project paths, source hashes, function names,
edit identities, expected outputs or corpus-specific thresholds may select an
optimized path. Fix general policies before the decisive comparison.

Required validation, maintenance and publication cannot move outside the timer.
A daemon may retain state from the preceding completed build. Record startup
and memory costs and wait for a validated revision before declaring readiness.
It must not see future edits or benchmark plans. If file watching starts work
before invocation, the strict clock starts when the edit becomes visible.

Ordinary one-time toolchain installation, dependency download, engine builds and
std-MIR preparation are setup, as in `BENCHMARKING.md`. Record them separately.
Each independent history starts with empty task-owned project targets and one
original-source build. Label that cold cost and later genuine warm costs; never
prebuild an edited state or copy its completed artifacts into a timed history.
Keep modes' project caches separate. Do not clear machine-wide caches.

## Correctness before performance promotion

Use targeted fixtures while developing a mechanism. Before its first real
timing, compare acceptance, diagnostics and runtime results with ordinary pinned
rustc, with reuse both disabled and enabled. An audit mode that recomputes cache
hits is preferred when a new proof boundary is introduced. Diagnostic comparison
may normalize owned checkout roots and machine-generated paths only; retain
codes, levels, spans, messages, children and lint expectation behavior.

Before promotion, cover each semantic boundary the mechanism could reuse:

- An ordinary body edit, an uncalled type error, an uncalled borrow error, a
  wrong runtime result caught by the original tests, and restoration after each
  failure. No stale successful artifact may execute after a failed build.
- A changed inline/generic body, constant or static initializer, layout and
  drop behavior, trait/impl candidate set, and an opaque/async hidden type.
  Include downstream consumers where the proposed mechanism crosses crates.
- Macro expansion and generated items, including an implementation introduced
  inside a body; relevant build-script/proc-macro inputs and unchanged generated
  output; `file!`, `line!` and caller-location effects after source movement.
- Configuration and cache transitions: features/cfg, target, rustflags/profile,
  tool identity, cache disabled/enabled, missing/corrupt/incompatible artifacts,
  and failed or interrupted previous builds. Unsupported cases must take a
  correct ordinary path or report an explicit error.

Apply this checklist at the changed mechanism's boundary, using existing tests
where appropriate. Each real history retains original/wrong-edit/restoration
controls and every selected original test after each build. Preserve outputs
and artifacts. Require exact bytecode equality for a runtime-only change;
compiler transformations may change bytecode but must preserve semantics.

Deferring required unsupported calls to runtime traps does not satisfy strict
readiness. Retain compatibility failures and exact workload scope: a selected
test group's success does not establish full libtest or application support.

## Fresh edited histories, orders and timing gate

The current `--cycles` harness returns to the same original and edited source
states. It is useful for diagnostics and regression comparisons, but repetition
of a previously compiled revision cannot be the decisive evidence here.

For the primary gate, use **three independently cold project histories**, each
with one original build followed by the five existing cumulative edits exactly
once. Each mode in a history compiles every valid edited source hash for the
first time; its preceding source hash must differ. Histories share installed
tools and downloaded dependencies, but not project caches or daemon state.
Original, erroneous and restoration commands are controls excluded from the
edited gate but included in session totals. Freeze any additional nonrepeating
edit sequence before running it.

Use candidate, unchanged baseline and an independent baseline duplicate with
separate real workspaces. Balance the three mode positions across the three
histories and use the existing within-history permutation machinery. Keep a
same-session ordinary native control with explicitly recorded dev/test profile,
incrementality, debuginfo, worker counts, test threads and flags. Native is a
reference, not an extra path from which to choose the fastest result per edit.
Diagnostic Cargo/self-profile instrumentation belongs in a separately labeled
run unless enabled identically and included in every timed arm.

For the target workload, publish all fifteen candidate edited observations,
and per-edit minimum/median/maximum across the three histories. Also report the
overall median, nearest-rank p95, maximum, paired baseline differences, child
and daemon CPU, cache hit/miss counts and peak/resident memory where available.
Do not sum overlapping/nested stage medians. Keep a whole-session total that
includes cold builds and correctness controls.

The **primary gate passes only if every one of the fifteen valid candidate
observations is below 0.500 s** at the strict boundary. With fifteen samples,
nearest-rank p95 is the maximum. No pooling across edits to hide a slow edit, no
fastest-of-N sample, and no replacement of a failed history by its best repeat.
The A/A observations describe same-session variability; they do not subtract
noise from the absolute threshold or turn these correlated edits into a
confidence interval. A borderline or noisy miss is still a miss for that run.

Holdouts use the same fresh-history and correctness design to test **generalized
improvement and no material regression**, without an absolute latency cutoff.
Report actual per-project times, paired differences and A/A variability. A
generalization claim requires observed build-readiness savings beyond the
observed A/A variation on fresh projects where the mechanism applies; cache
hits or Nushell savings alone are insufficient. Report unaffected and slower
projects too, and do not tune the candidate using sealed holdout results.

A reproducible median wall or CPU increase above 5% on a holdout or exposed
regression control blocks default adoption until explained and fixed. The 5%
rule triggers investigation; it is not a noise allowance against Nushell's
0.500 s gate. Disclose cold/setup and memory regressions. Holdout compatibility
or correctness failures fail that evaluation even if the timings are fast.

## Holdout isolation and selection

All five projects in `benchmarks/corpus.json`, all nine entries in
`benchmarks/workflow-corpus.json`, and prior interface-edit cases are **exposed
development/regression data**. Some historical reports call them held out; they
cannot serve as fresh holdouts for this campaign. Another worktree, revision or
test selection of one of those projects does not reset that exposure.

There is no declared fresh-project holdout manifest. Local directory names do
not establish authorization or lack of exposure. This document freezes the
following public pool and selection procedure; no entry is yet pinned, adapted,
compiled or measured:

| Stratum | Closed repository pool |
| --- | --- |
| Application | `github.com/sharkdp/bat`, `github.com/casey/just`, `github.com/ajeetdsouza/zoxide` |
| Library | `github.com/clap-rs/clap`, `github.com/toml-rs/toml`, `github.com/serde-rs/json` |
| Large development workspace | `github.com/rust-lang/cargo`, `github.com/rust-lang/rust-analyzer`, `github.com/rust-lang/rustfmt` |

Before any holdout timing, an evaluator separate from implementation work must:

1. Record known prior exposure. Exclude a repository only for documented prior
   use in this project's optimization, duplicate lineage, unavailable source,
   or license/access restrictions; never for an unfavorable measured latency.
2. Rank eligible URLs within each stratum by the hex SHA-256 of UTF-8
   `strict-warm-build-v1\n` followed by the exact table URL, ascending. Select
   the first repository in each stratum. Freeze immutable source commits,
   toolchain, lockfiles, profiles/features and commands in a committed manifest.
   Select pins from repository metadata before implementation-source inspection
   or timing; retain exclusions and the reserve ranking.
3. After the implementation and global configuration are frozen, inspect those
   selected sources only to define five legitimate cumulative production-body
   refactors per project, exercised by existing unchanged tests. Include at
   least one edited package with a real downstream consumer in the application
   or workspace stratum. Freeze rationale, patches and tests before compilation;
   do not tailor them to the optimized path.
4. Validate the adapter and source mutations against ordinary rustc, with no
   candidate timing feedback to the implementation agent. Freeze hashes of the
   manifest, patches, original tests, adapter and complete command plan before
   running the candidate. Retain adapter and candidate failures; do not replace
   a failed candidate holdout with an easier reserve.

The existing case loader permits only exposed projects and revisions. Qualify a
new-project adapter and verifier; do not reuse an old corpus label for new code.

Run the sealed evaluation only after the development gate passes. Inspecting
holdout profiles/timings to change the implementation consumes that holdout for
development. Preserve the failed campaign; a new sealed evaluation uses the
next predetermined reserve and a new manifest. If the pool is exhausted, report
no fresh confirmation rather than expanding it in response to speed results.

## Practical stages and retained failures

1. **Attribution:** freeze a small instrumented Nushell history to locate actual
   elapsed work. Count only compiler processes actually invoked; Cargo may
   replay cached diagnostic reports. This stage has no 0.5 s success claim.
2. **Mechanism screen:** relevant correctness tests, then one complete fresh
   five-edit Nushell history against the frozen baseline. Stop further timing
   of an ineffective candidate; preserve findings and choose another measured
   bottleneck. Full corpus/holdout runs are unnecessary for every experiment.
3. **Qualification:** complete the changed mechanism's semantic checks, three
   fresh primary histories, and the exposed-corpus regression controls. Freeze
   the exact candidate commit/tool key/options before the final gate.
4. **Sealed evaluation:** run the frozen new-project holdouts once under their
   complete plan. Publish all successes, unsupported cases and failures with
   exact scope before describing the generalization result.

Serialize this task's builds, tests and benchmarks with the shared repository
benchmark lock, including across worktrees. Record task-owned process identities
and bounded lock admission. Do not control, stop, reprioritize or clear caches
belonging to other sessions. Record host contention; do not filter slow samples
because another workload was active.

A crash, wrong result, unsupported operation, timeout, storage exhaustion,
missing receipt or changed measured source is failed/incomplete, never a passing
short sample. After fixing a concrete cause, freeze a new attempt and rerun the
complete affected history or gate with fresh caches; retain both attempts.
Do not splice prefixes, rerun individual slow observations, extend samples until
passing, or revise thresholds or workload scope in response to results.

Commit the protocol, source/tool identities, manifest/patch hashes, exact
commands, raw receipts, control outcomes, artifact/output hashes and assessment.
Private raw material remains under `.work` with approved aggregates only. Merge
with current `main` and push qualified changes as they land, while keeping
in-progress source and measurement identities immutable. A changed tool or
relevant harness starts a new comparison rather than altering a completed run.
