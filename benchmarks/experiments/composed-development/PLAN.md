# Composed development candidate

Prospective implementation of the September 12 review, starting from main
cb474883f12f089183681470302fdbfc97b0f373. This is one new composition of
previously qualified mechanisms. Earlier standalone performance gates and
their failed decisions remain unchanged. No component needs an independent
8% win to enter this experiment; correctness and combined command latency
decide whether to retain the combination.

## Source composition

* Whole-call expansion: `whole-call-inline/inject.py`, as qualified by
  `results/whole-call-build-02/summary.json`. Bounded direct acyclic calls,
  CFG definite initialization, existing growth and ABI bounds. Eleven tests.
* Call-slot hints: `call-slot-fast-path/inject.py`, as qualified by
  `results/call-slot-build-01/summary.json`. Hints retain equality guards and
  checked fallback using actual runtime values. Eight tests.
* Budget register: `aggregate-byte-writes/budget_register.py`, as qualified
  by `results/budget-register-build-02/summary.json`. x22 across internal
  resumable edges; publish at every external exit. Four tests.
* Fixed frame clearing: exact mechanism and three tests from commit 46134e4,
  relative to ae0a49e. Clear the proved frame extent plus alignment padding
  up to 256 bytes; preserve the dynamic fallback and separate register buffer.
* Function reuse: the existing strict compiler-validated cache in main,
  exposed by an explicit `--function-cache reuse` launcher option. Require
  exporter capability, pass the environment option only to Cargo, reject
  discovery/audit/allocation tracing and keep the default off. This replaces
  experimental subprocess monkeypatching. No lazy type or borrow checks.
  The first real pgrust command exposed its repository `incremental=false`
  profile. A follow-up adds explicit `--function-cache auto`, requiring its
  own exporter capability: reuse only with an incremental session and enabled
  compiler dependency graph, otherwise full lowering with a recorded reason.
  Forced reuse keeps its error when tracking is unavailable. Preserve repository
  profile settings; do not enable incremental compilation implicitly.
* Prepared execution and explicit suite workers are already on main; fix
  their settings on both custom routes in the performance comparison.

The qualification build freezes every Rust source, Cargo input and this plan
with its actual source commit and binary hashes. Check interactions, especially
x17 scratch clobbers, x22 budget exits, inlining closure changes, and slot-hint
fault ordering. Do not infer combined correctness from old individual tests.

## Qualification before performance

Host qualification floor: 4 GiB. This uses the populated existing
`.work/fixed-frame-clear-combined-build-01/target` debug/release dependency
cache, two Cargo workers, locked offline dependencies and no incremental host
compilation. It does not admit a fresh large-project cache. Respect the global
benchmark lock and preserve unrelated workloads. Stop a stage before starting
if its free-space floor is not met.

Run all Python harness tests, then 392 Rust tests in each of debug and release
with one ignored per profile, including generated CFG differential coverage.
The initial build passed 391/profile; automatic cache eligibility adds one test.
Build the current exporter and wrapper as well as the custom VM. Record failed
attempts and fixes separately; do not overwrite qualification evidence.

Run retained original token, folded and pgrust bytecode through the combined VM
and retained VM with the same inputs and original assertions. Use individual
recorded entropy inputs where exact counter agreement is required; do not
inject the process-global entropy shim into concurrent suites. Check normal
entropy suites with matched workers. Exercise strict checking, cache off/reuse
alternation, real valid and wrong edits, source restoration, catalog binding
and original native outcomes. New inlining may change bytecode and logical
instruction counts across exports; compare equivalent exported artifacts when
requiring exact interpreter/JIT agreement.
Qualify automatic mode under both enabled and disabled incremental profiles,
including helper edits, type/borrow rejection and restoration. A failed Cargo
check must stop before VM execution; previous successful artifacts may remain.
If the rebuilt VM bytes match the first qualified VM, retain its exact saved-
input qualification by binary hash rather than rerunning unchanged VM checks.

## Subsequent experiment contract

Before any latency sample, freeze a separate driver and concrete manifest with
the qualified tool key, source pins, original test names, exact edit schedule,
cache namespaces, workers, storage estimate, stopping rule and paired order.
Use one fresh same-session A/A control and fifteen edited pairs for each
primary comparison; A/A envelopes describe observed noise, not confidence
intervals. Never splice interrupted pairs or repeat an unchanged failed
candidate to seek a pass. Wrong edits and restoration are correctness controls,
not performance samples. Unchanged build loops do not decide adoption.

Compare against both 9637b0ac on its original selection and the current
selected-suite anchor. Keep prepared execution and worker counts matched
where supported; disclose older anchor interface limits rather than silently
changing its workload. Ordinary Cargo/libtest with default test concurrency
is the primary native control, using two Cargo build workers. Include a
practical line-tables native control and preserve repository-default results.
Isolated native controls remain useful for matched isolation semantics.

Require a material 8% combined command-wall improvement on the compute-heavy
primary, no CPU regression beyond the predeclared A/A allowance, and held-out
wall/CPU guards. Do not credit scheduling or test-selection changes to emitter
efficiency. Keep defaults unchanged until this combined experiment and its
held-outs pass. Use measured frontend/export/preparation/execution costs to
choose the next call-protocol or unchanged-function-binding implementation.
