# Continuation checkpoint — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test measurements. Every item in the user-owned,
unmodified `suggestions.txt` has a [decision](docs/SUGGESTIONS-REVIEW-20260910.md).
Local Git commits are authorized; no remote or push was requested.

## Active work

Branch `experiment/resumable-native-calls`. Runtime `5574d10`, integration
`e1bec3e`, bulk initialization `001065a`, installed tool `78e60cdd`. The custom
AArch64 emitter executes resumable Calls/Returns over initialized guest frames,
with exact descendant VM continuation, one host ABI frame and no recursive
host-stack growth. Known large frame/register ranges now clear in exact 64-byte
batches. Every required byte, argument-copy order and budget check is preserved.
The option remains `--jit-resumable-calls` with optional persistent registers;
it excludes tree/stub mode and stays disabled by default.

- All **257 workspace tests pass in debug and release**, one ignored. The new
  emitted-code test checks dirty ranges, conservative minimums, all alignments
  modulo 64, boundaries through 4096 bytes and an empty one-past-end. Existing
  recursion (through 1024), descendant fallbacks, full host ABI, budget/storage/
  capacity, warm alias copies and TLS/profile tests pass.
  [Qualification](results/resumable-bulk-release-01/assessment.md).
- [Twelve CLI checks](results/resumable-bulk-cli-01/summary.json), four historical
  workflow verifications and [both original artifacts](results/resumable-bulk-real-smoke-01/assessment.md)
  pass. Folded has identical 4,138,403,285 instructions and 25,913,904 native
  Calls. Token retains original randomness. Code sizes are 5,867,588 and
  14,722,684 bytes, with zero declined functions. The exporter is byte-identical
  to the preceding resumable tool. [Build index](benchmarks/tool-builds.json).

[The completed bulk E2E run](results/resumable-bulk-e2e-01/assessment.md) verified
168 commands, 30 edited pairs and 84 identical paired artifacts. Folded improves
**19.51% paired** and token **19.95%** against original b2; CPU improves 20.60%/
20.54%. Folded passes. Token's ratio is **0.8004639304**, just above its original
0.8 maximum, so the combined numerical gate fails. Do not round it into a pass.
Native remains faster on both. The first resumable tool (`035ef708`) improved
folded 10.6% and token 15.0%; cross-run differences are not isolated component gains.

[The single replication](results/resumable-bulk-e2e-02/assessment.md) is complete:
folded improves 19.15% and token 19.97%, with CPU improving. Token's ratio
0.8003441753 again narrowly misses 0.8; both combined numerical gates fail.
[The two-run report](results/resumable-bulk-replication-01/assessment.md) preserves
336 commands, 60 edited pairs, 168 artifacts and per-edit wall/CPU variation.
Corresponding histories match across runs; cross-cycle layout differences remain
unresolved. No more repeated attempts or batch-size tuning are planned.

Broader native/TLS/fre compatibility checks pass. The seven-workflow held-out
run is **incomplete after ENOSPC in its final Nushell type-relations case**.
[Failure and recovery](results/resumable-bulk-heldout-failure-01/assessment.md)
preserve stale status receipts, logs and partial timings. All matching run
processes were gone; the owned source matched the exact expected edit and was
restored to its pinned bytes. No cache cleanup or process signaling was needed.

Six completed workflows were reverified: pgrust paired wall −1.88%, Nushell +0.60%,
rg-aot −0.03%, fre TLS −1.58%, pgrust SHA-1 −4.38%, Ruff −0.56%. None exceeds
5%; there is no complete seven-case result. Preserve these 504 commands, 90 pairs
and 252 artifacts separately from the incomplete last case's 12 primary records
and three check records. Retry only the missing case with a new run/cache identity.

The harness now stages source restoration before mutation, publishes source and
JSON atomically, waits/drains children on receipt failures and checks free space
before commands. [Ten failure-injection checks](results/workflow-io-faults-01/summary.json)
pass using three real child processes. Actual integrated Rust qualification is
next: one pgrust interface cycle, then the missing Nushell workflow. Runtime/tool options and failed primary gates are unchanged.

The next workflow check is [generic interface edits](benchmarks/experiments/interface-edits/PLAN.md):
pgrust's byte-hash API becomes generic over borrowed `AsRef<[u8]>`, and Nushell's
list-type constructor accepts `Into<Type>`. All original test source is preserved.
Two pinned case files, a bounded public case loader and input-check helper are
committed in `38962af`. The input helper now passes two valid specifications and
25 malformed/tampered cases; no Rust interface edit has run yet. The harness
and independent verifier now integrate frozen case snapshots and reconstruct
all source states/selections/orders. Qualify one pgrust cycle, retry the missing
held-out case, qualify Nushell, then fifteen cycles of each single interface edit.

The [broader driver](scripts/qualify_native_execution.py) now stages the existing
full validator with immutable tool/mode selection and unchanged assertion ASTs.
Its [helper qualification](results/resumable-execution-driver-01/summary.json)
passes three staging configurations and both archived mode checks; false
resumable claims are rejected. Full new-tool execution now passes all 47,004
mixed commands in `resumable-bulk-native-01`, including 22,238 JIT invocations
with the exact options and real native Call/Return counters. No successful JIT
run declined functions. The separate `resumable-bulk-tls-01` passes 245 commands,
including original destructor order/reset and normal callbacks. Both are terminal0.
The tracked fresh-body coordinator and explicit audit tool selection preserve
old audit assertions; 18 CLI checks pass on the committed driver source.
The [fresh fre replay](results/resumable-bulk-fre-01/assessment.md) is complete:
382 original bodies pass and seven are ignored, with 382 fresh native executions.
All 382 compared artifacts match the older replay; no outcomes changed.
Successful bodies executed 959,714,888 native Calls and 976,181,341 Returns.
Maximum code is 15,173,088 bytes with zero declined executions. Allocation limit
150,000, unsupported-call trapping, normal callbacks and recorded MIR settings
remain required. This is body replay, not full libtest. Held-out workflows remain.
[Broader recipe](benchmarks/experiments/resumable-native-calls/BROADER-QUALIFICATION.md).

Exact-code profiles of `035ef708` resolved every generated PC across three
windows each. Required zeroing accounted for 56.3% folded /17.4% token samples,
and token native-boundary self 13.5%. These partial perturbed windows motivated
bulk clearing; they are not speedup forecasts or current-tool profiles.
[Folded](results/resumable-folded-sample-01/assessment.md),
[token](results/resumable-token-sample-01/assessment.md).

The qualified [private-array census](results/aggregate-reuse-weights-01/assessment.md)
found only 0.0000073% additional folded frame-byte scope and 0.1233% token.
That layout change remains parked, alongside argument-only zero elision and
unused-MIR-local removal. Broader aggregate reuse still needs padding/alias/
lifetime proofs; do not restart batch-size/opcode tuning by default.

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
semantic equivalence or an established cause. The broader 47,004 mixed commands
include 22,238 JIT and 22,238 interpreter invocations across two inlining modes;
these are not unique test cases. [Recount](results/historical-validation-counts-01/assessment.md).
The historical 245 TLS checks and 382 passing/7 ignored fre bodies used
older `57a54edd`. Current `78e60cdd` now has separate fresh qualification above;
older coverage was not transferred. Both fre replays
uses allocation limit 150,000, unsupported-call traps and normal try callbacks;
it is not an unfiltered libtest run. See [STATUS](STATUS.md).

## Ownership and recovery

Only `resumable-bulk-heldout-01` is active: supervisor 79695, controller 79698;
it started with pgrust child 79700. All earlier runs are terminal0. Freeze all
Rust/corpus/interpreter/verifier inputs until terminal. Then run
`evaluate_gates.py --run-id resumable-bulk-heldout-01 --source-commit 001065a --held-out`.
Expected totals are 588 commands, 105 edited pairs and 294 artifacts. The extended
evaluator already reproduces both existing primary receipts exactly, without
overwriting them. Both token failures persist. Inspect exact receipts before acting.
The unbounded goal remains active.

Detailed current state, exact tool hashes, all five source pins and terminal
receipts are in `.work/continuation-state.json`. Toolchain is
`nightly-2026-09-08`, rustc `cea272fa3`. Private adapter is
`.work/private/workflow-rg-aot.json`; public reports contain aggregates only.

No subagents or independent model calls. No AWS activation, unrelated process
control, broad cache deletion, private cleanup or quarantine deletion. A separate
user-owned cleanup task takes `.work/benchmark.lock`; wait without controlling it.
Serialize task builds/tests/benchmarks/cleanup with that lock. Preserve artifacts,
assertions, wrong-edit controls, source restoration and historical evidence.
