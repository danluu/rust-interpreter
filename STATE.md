# Continuation checkpoint — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test measurements. Every item in the user-owned,
unmodified `suggestions.txt` has a [decision](docs/SUGGESTIONS-REVIEW-20260910.md).
Local Git commits are authorized; no remote or push was requested.

## Active work

Branch `experiment/aggregate-reuse-census`, runtime commit `d664bce`, installed
tool `e89de7f8`. Bounded full-CFG liveness (`b252588`) and up to three persistent
u128 register pairs now span native branches and calls. VM continuations spill
live values before returning, and native children preserve assigned host GPRs.
Analysis limits decline to the existing emitter. The option stays experimental.
[Plan and implementation](benchmarks/experiments/bounded-native-calls/VALUE-LIFETIMES-NEXT.md).
[Exact ABI](benchmarks/experiments/bounded-native-calls/INTERNAL-ABI.md).

- All 240 workspace tests pass in [debug](results/persistent-native-04/summary.json)
  and [release](results/persistent-release-01/summary.json), one ignored. Existing
  cache, local-memory and native-call helpers exercise both register modes.
  New checks cover wide loops, VM fallback, far registers, budgets and x19–x28,
  SP/LR through 64 native children, on returns and faults. The initial ABI test
  omitted the valid PC 4 budget continuation; failed `persistent-native-02` is
  preserved and corrected checks `03`/`04` pass.
- [Ten CLI checks](results/persistent-cli-01/summary.json) pass, including rejected
  option combinations. The receipt verifier rechecks both historical workflows
  and rejects falsely claimed runtime flags. [Build index](benchmarks/tool-builds.json)
  reconstructs the Git source key and verifies installed binaries.
- [Both original artifacts](results/persistent-real-smoke-01/assessment.md) pass
  with all assertions and existing limits. Persistent assignments publish in
  100 folded / 228 token code instances; three token analyses decline at bounds.
  Token uses guest random bytes; its independent instruction counts differ and
  do not prove identical traces. This smoke check is not E2E performance evidence.

The [completed E2E run](results/persistent-e2e-01/assessment.md) contains 168
commands, 30 edited pairs and 84 identical paired artifacts. All flags, source
pins and restoration are verified. Token improves 23.6% paired (CPU −23.6%);
folded improves 4.2% (CPU −3.9%). Token passes its original 20% target, folded
misses 10%; the combined gate fails. The options remain experimental.
Marginal command medians: folded native 1.634 / b2 2.472 / candidate 2.373 s;
token native 1.952 / b2 6.482 / candidate 4.959 s. Native remains faster on both.

Fresh three-window [folded](results/persistent-folded-sample-01/assessment.md)
and [token](results/persistent-token-sample-01/assessment.md) captures pass original
assertions and resolve all generated PCs. Folded has 24.9% VM frame reservation,
9.0% generated zeroing and 3.6% direct register-array stores. Token has 4.2%,
12.8% and 7.4%, respectively. These are perturbed shares, not savings estimates.
The helper rechecks all 12 old/new windows with unchanged counts and hashes;
its initial tuple-versus-JSON-array comparison failure remains documented.

The [additional private-array census](results/aggregate-reuse-weights-01/assessment.md)
is complete and rules out that narrow optimization: only 3,116 additional bytes
across 42.5 billion folded direct-call frame bytes (0.0000073%) and 0.1233% for
token. The isolated observer (`f9bd49c`, tool `71605527`) passes 15 exporter/observer
tests and uses the exact `e89de7f8` VM. Both fresh exports are byte-identical to
the original artifacts and pass original assertions. New profiles also pass.
Three typed weighting tests pass; actual function IDs and every profile operation
are verified, with exact instruction accounting and no unattributed direct frames.
All three runs are terminal with return code zero. No production layout changed.

Next implement [resumable native Calls](benchmarks/experiments/resumable-native-calls/PLAN.md)
over an explicit guest frame stack. Begin with initialized/stable frame backing,
documented host layout and typed continuation invariants, then emitted Call/Return
and VM integration behind an experimental option. A descendant must resume at its
actual frame/PC after an unsupported operation, budget tail or preparation
boundary. Do not map guest recursion onto host-stack recursion. Preserve complete
initialization, argument/error order, result copies, full-width registers,
profiling, guest budgets and root/TLS completion. This removes whole-function
eligibility restrictions; it does not promise to remove frame-clearing costs.

Keep the original b2 gates. Seven held-out workflows and broader native/TLS/fre
qualification remain required before retention; no unresolved >5% held-out
regression is allowed. These broader suites have not been run on `e89de7f8`.

## Evidence guiding this experiment

The [ordinary native-Call result](results/native-region-e2e-01/assessment.md),
`26833c3` / `2f31c6a0`, completed 168 commands, 30 edited pairs and 84 identical
paired artifacts: token improves 19.3% paired, folded regresses 1.4%. Both gates
fail. The earlier [bounded-tree result](results/bounded-native-e2e-01/assessment.md)
improves token 14.4% and regresses folded 3.0%; it also fails both gates.

Diagnostic `059d818` / `7ad1ccdb` passes 233 debug/release tests and emits exact
same-process code/range dumps. Three-window profiles pass original assertions:
[token](results/native-code-token-sample-02/assessment.md) has 14.0% direct
register-array stores / 11.7% native zeroing; [folded](results/native-code-folded-sample-01/assessment.md)
has 6.0% stores / 8.2% native zeroing and 23.1% VM frame reservation. These are
partial perturbed samples, not predicted savings. All generated PCs resolve.
The first token capture missed its initial arena; its incomplete evidence and
the bounded-readiness fix/complete retry are preserved.

Frame layout/lifetime changes stay separate. Argument-only zero elision already
had little scope (4.4% folded / 9.1% token), as did removing unused MIR local
storage. Do not repeat those parked experiments. Aggregate lifetime reuse needs
a new alias/initialization proof and changed-artifact controls. Private primitive
arrays now join those parked directions; broader aggregate reuse is unproven.

## Qualified controls and coverage

Default comparison source `a2a0e04`, tool `b2aa6efe`, passed 202 workspace tests.
Its [nine-workflow corpus](results/native-controls-corpus-01/assessment.md)
completed 756 commands, including 189 independent Cargo checks, 135 edited pairs
and 378 verified artifacts. Pins for pgrust, fre, Nushell, Ruff and private
rg-aot were restored. Native uses root O0/incremental, 18 jobs and default test
concurrency; custom uses four jobs. Package overrides remain; linker/backend/
worker alternatives are unqualified. Cold commands exclude toolchain/dependency/
std-MIR setup and OS-cache clearing. All samples remain in the records.

All three fre workflows have unresolved cross-history bytecode layout changes;
corresponding engines receive identical bytecode. Do not claim cross-history
semantic equivalence or an established cause. The broader 47,004 native commands
(23,502 cases × two inlining modes), 245 TLS checks and 382 passing/7 ignored fre
bodies belong to older `57a54edd`, not the current experiments. That fre replay
uses allocation limit 150,000, unsupported-call traps and normal try callbacks;
it is not an unfiltered libtest run. See [STATUS](STATUS.md).

## Ownership and recovery

All current task executions are terminal; no sampler, build or benchmark is
active. The unbounded goal remains active and the next diagnostic is authorized.

Detailed current state, exact tool hashes, all five source pins and terminal
receipts are in `.work/continuation-state.json`. Toolchain is
`nightly-2026-09-08`, rustc `cea272fa3`. Private adapter is
`.work/private/workflow-rg-aot.json`; public reports contain aggregates only.

No subagents or independent model calls. No AWS activation, unrelated process
control, broad cache deletion, private cleanup or quarantine deletion. A separate
user-owned cleanup task takes `.work/benchmark.lock`; wait without controlling it.
Serialize task builds/tests/benchmarks/cleanup with that lock. Preserve artifacts,
assertions, wrong-edit controls, source restoration and historical evidence.
