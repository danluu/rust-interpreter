# Continuation checkpoint — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test measurements. Every item in the user-owned,
unmodified `suggestions.txt` has a [decision](docs/SUGGESTIONS-REVIEW-20260910.md).
Local Git commits are authorized; no remote or push was requested.

## Active work

Branch `experiment/resumable-native-calls`. Runtime `5574d10`, launcher/gate
integration `e1bec3e`, installed tool `035ef708`. The dedicated custom AArch64
emitter now executes direct Calls and Returns over initialized guest frames.
It compiles one body per function, preserves the complete external host ABI,
reloads per-function persistent registers on transitions and returns the actual
descendant frame/PC to the VM at unsupported operations or budget/storage/code
readiness boundaries. Guest recursion does not consume recursive host frames.
The option is `--jit-resumable-calls`, optionally with persistent registers; it
excludes the old tree/stub options and stays disabled by default.

- All **256 workspace tests pass in debug and release**, one ignored:
  [debug](results/resumable-native-03/summary.json),
  [release](results/resumable-release-01/summary.json). Seven new execution tests
  add looping/recursive callees (through depth 1024), deepest VM fallbacks,
  budgets, preparation boundaries, all required GPRs/SP/LR, warm ordered/alias
  copies through 257 bytes, and rejected option combinations. Existing native
  call, error-order, heap-growth and TLS suites now also run the new mode.
  Profile checks compare full logical per-PC counts, not just output values.
- [Twelve CLI checks](results/resumable-cli-01/summary.json) pass. Four historical
  workflow receipts still verify; false claims of the new runtime option are
  rejected. Launch commands, timing metadata and gates carry the new flag.
  [Build index](benchmarks/tool-builds.json) reconstructs source and binary hashes.
- [Both original real artifacts](results/resumable-real-smoke-01/assessment.md)
  pass all assertions. Folded executes 25,913,904 native Calls with 85,769 native
  entries versus b2's 43,732,357 entries, with identical logical instructions.
  Token executes 110,504,850 native Calls. Both stay within the original code
  budget with zero declined functions. Token uses randomness; independent
  instruction counts differ. This smoke run is not E2E performance evidence.

[The completed E2E comparison](results/resumable-e2e-01/assessment.md) verified
168 commands, 30 edited pairs and 84 identical paired artifacts. Folded improves
10.6% paired (CPU −11.4%) and token 15.0% (CPU −14.7%) against `b2aa6efe`.
Folded passes its original 10% target; token misses 20%, so the combined gate
fails. Native remains faster on both. No default retention. Next qualify profile
helpers and capture three exact-code windows of this tool on each original
artifact, then use the measured call/transition costs to select the next change.
Seven held-out workflows and broader native/TLS/fre qualification have not run
on this tool; they remain required before retention.

[Design/qualification plan](benchmarks/experiments/resumable-native-calls/PLAN.md)
and [emitter contract](benchmarks/experiments/resumable-native-calls/EMITTER-NEXT.md).
Groundwork `fca1e96` / `1264921` qualified initialized frame backing and checked
cursor publication before emitted execution; its 249-test count is historical.

The preceding E2E result is
[persistent-e2e-01](results/persistent-e2e-01/assessment.md), tool `e89de7f8`,
Git `d664bce`: 168 commands, 30 edited pairs, 84 identical artifacts. Token
improves 23.6% paired and folded 4.2%; only token passes. Marginal command medians
are folded native 1.634 / b2 2.472 / candidate 2.373 s and token native 1.952 /
b2 6.482 / candidate 4.959 s. Native remains faster on both in that run.

The qualified [private-array census](results/aggregate-reuse-weights-01/assessment.md)
found only 3,116 additional bytes across 42.5 billion folded direct-call frame
bytes (0.0000073%), and 0.1233% token. That narrow layout change is parked. No
production frame layout changed. Broader aggregate reuse still needs padding,
escape and lifetime proofs; do not resume narrow opcode/frame tweaks without
new end-to-end evidence.

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
