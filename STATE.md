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

Broader native/TLS/fre compatibility checks pass. All seven held-out cases are
now complete across two run histories. [The recovery assessment](results/resumable-bulk-heldout-recovery-01/assessment.md)
verifies **588 commands, 105 edited pairs and 294 artifacts**, original controls,
source restoration and both archived harness versions. No paired wall regression
exceeds 5%: pgrust −1.88%, Nushell +0.60%, rg-aot −0.03%, fre TLS −1.58%,
pgrust SHA-1 −4.38%, Ruff −0.56%, Nushell type relations −0.86%.
The last case's paired CPU change is +1.79%; small changes are not significance
claims. Original primary token gates remain failed; no default retention.

The original seven-case run remains **incomplete after ENOSPC**. Its six complete
cases are preserved, with its partial last-case 12 primary/three check records
outside the new complete totals. [Failure and recovery](results/resumable-bulk-heldout-failure-01/assessment.md)
record exact source restoration with no signals/cache cleanup. Retry01 was
rejected for a mistyped key before compilation; retry02 completed successfully.
The new assessment verifies original harness `edf0c2b` and retry harness `e4a9613`
from Git rather than pretending the IO changes were present in the first run.

The harness stages source restoration before mutation, publishes source/JSON
atomically, waits/drains children on receipt failures and checks disk before
commands. [Ten fault checks](results/workflow-io-faults-02/summary.json) pass using
three real children. [Pgrust's actual generic API qualification](results/interface-pgrust-qualification-01/assessment.md)
passes all four original tests and wrong-edit/source/artifact controls: nine
primary commands, three checks, six paired artifacts. This is one edited pair.

Both [generic interface qualifications](benchmarks/experiments/interface-edits/PLAN.md)
now pass with original assertions, wrong edits, six paired artifacts each and
source restoration. Pgrust generalizes borrowed hash inputs; Nushell generalizes
its list-type constructor to `Into<Type>`. These single pairs remain separate
from the repeated measurements.

[Pgrust's fifteen-cycle comparison](results/interface-pgrust-repeated-01/assessment.md)
is complete: **180 commands, 15 edited pairs, 90 paired artifacts**. Median wall
is 0.663s native, 0.495s baseline, 0.491s candidate; paired changes −1.14% wall/
−1.17% CPU. Original source-state artifacts match across all cycles. This is
one API edit repeated fifteen times, not the original five body edits × three.
Nushell's fifteen-cycle run is active as `interface-nushell-repeated-01`,
supervisor23231 (controller identity in its status receipt). Wait for terminal,
verify the snapshot/commands/artifacts, frozen inputs and source restoration,
then report both interfaces together without pooling their different costs.
Keep case, interpreter, verifier and Rust sources frozen while it runs.

The completed Nushell held-out median is 8.242s native, 5.198s baseline and
5.159s candidate. Candidate Cargo is 5.082s versus 0.01044s VM execution.
Host build dependencies include nu-cmd-extra's theme generator importing
nu-protocol; keep that real cost. These stage results favor investigating
frontend/build reuse for this workload after the interface comparisons; they
do not establish a safe invalidation shortcut or a whole-application win.

The next [compiler-pipeline diagnostic](benchmarks/experiments/compiler-pipeline/PLAN.md)
reuses the existing `--cargo-timings` harness on one complete Nushell interface
cycle after the repeated run. New `scripts/cargo_timing_data.py`,
`scripts/analyze_cargo_timings.py` and `check_timing_parser.py` are prepared,
**not yet executed**. First run the helper under the benchmark lock, then the
instrumented cycle and its ordinary verifier, then analyze hashed snapshots.
Keep compiler-unit overlap/duplicate descriptions distinct from CPU or critical
path attribution. An older profile already captures the host/library/test chain.
The [current read-only inventory](results/compiler-unit-fingerprints-01/assessment.md)
finds three nu-protocol configurations in all four completed histories,
including native and independent check. Features, profile hashes and flag
handling differ; do not attribute the three-unit count solely to custom
`--target`, remove dependencies, or assume name-only artifact sharing is valid.

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
