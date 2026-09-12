# Current state — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test benchmarks. Every item in `suggestions.txt`
has an [explicit decision](docs/SUGGESTIONS-REVIEW-20260910.md); that user-owned
file remains unchanged and untracked. Local commits are authorized; no push.
Branch: `experiment/resumable-native-calls`.

## Integrated compiler

The aggregate-frame relocation exporter is source `5b2330c`, tool `9637b0ac`.
Its exact qualified source is integrated into the normal workspace.
It reuses storage for nonoverlapping MIR locals with emitted-byte write proofs,
normal-return edge handling, named origins, and checked ABI/scratch relocation.
All VM initialization remains. VM and wrapper binaries are unchanged.
The ordinary launcher selects this compiler; runtime options remain explicit.

Its [primary comparison](results/aggregate-relocation-e2e-01/assessment.md)
passes both predeclared gates (168 commands, 30 edited pairs, 84 artifacts):

| Case | Paired wall | Paired CPU | Native median | Control | Candidate |
| --- | ---: | ---: | ---: | ---: | ---: |
| Folded trie | −12.77% | −12.89% | 1.702s | 1.939s | 1.696s |
| Token phrase | +3.70% | +3.33% | 1.965s | 4.290s | 4.462s |

The candidate passes [39 compiler tests](results/aggregate-relocation-build-01/summary.json),
[1,024 differential VM executions](results/aggregate-relocation-fixtures-01/summary.json),
[47,004 broad validation commands](results/aggregate-relocation-native-01/assessment.md),
[245 TLS/destructor commands](results/aggregate-relocation-tls-01/assessment.md), and
[382 fre bodies, seven ignored, with fresh native controls](results/aggregate-relocation-fre-01/assessment.md).
Original assertions and strict type/borrow rejections remain.

All [seven held-outs](results/aggregate-relocation-heldout-recovery-01/assessment.md)
now pass their separate 5% wall/CPU guards: 588 commands, 105 edited pairs and
294 artifact hashes verify. Paired wall changes range from −0.28% to +2.71%;
CPU changes from −0.27% to +2.21%. Native/control/candidate absolute times are
reported separately; no pooled speedup. Private output is aggregate-only.
The original Ruff stop remains preserved and its five partial pairs excluded.

Recorded [capture/finalization costs](results/aggregate-relocation-pass-costs-01/assessment.md)
are 41.9 ms folded and 189.5 ms token. Token execution saves only 79.3 ms paired,
against 237.4 ms more Cargo time. These are completed-run observations, with
other pass effects and shared-host noise; the components do not prove causation.

## Immediate continuation

The aggregate compiler is integrated and qualified. The ordinary launcher selects
its exact measured source key. The [normal workspace qualification](results/aggregate-integration-root-01/assessment.md)
passes 289 debug and release tests (one ignored) and reproduces all three
executables byte-for-byte. The isolated guarded Call VM is qualified but parked after its fixed primary gate failed.

The x22 budget-register experiment is parked after its [fixed primary decision](results/budget-register-primary-01/assessment.md).
It passes broad correctness, native/TLS/fre replay and original-artifact checks,
but token paired wall improves only 1.01%, below the 10% target and inside its
3.99% A/A envelope. Folded improves 1.16%, also inside its 2.45% envelope.
All four complete histories, failures, entropy accounting and exact tools remain.
No budget held-outs or tuning retries are planned; the ABI is not integrated.

The [six exact-artifact profiles](results/aggregate-relocation-profiles-assessment-01/summary.json)
remain the next diagnostic inputs. Native Call and Return entries account for
3,030 of 7,562 token thread samples, including clearing and copies. Sample shares
are not speedup predictions: budget accesses were 10.06% of token samples but
did not produce a meaningful complete-command gain.

The [typed Call census](results/call-slot-census-02/assessment.md) now completes:
eight focused tests, both exact original profiles and all logical/native counters
verify. Known caller-frame slots cover 99.49% of token's 326,206,317 native argument
checks and 98.08% of folded's 82,536,622. No function hit an analysis bound. No new
guest execution or runtime change. The first receipt-path admission failure is
preserved with its source; the corrected check follows the exact smoke summary.

The [guarded Call argument path](benchmarks/experiments/call-slot-census/FAST-PATH-NEXT.md)
is implemented in isolated tool `ac38fa59`, VM `af5dd300`, from integrated
source `5b2330c`. The exporter and wrapper are byte-identical to control `9637b0ac`.
[Debug/release qualification](results/call-slot-build-01/assessment.md) passes
297 tests, one ignored. Eight new tests cover the static hints, mismatched
entry registers, faults/partial copies, budgets/profiles, large registers and ABI.
Root Rust sources and the parked budget ABI remain unchanged.

The [original-artifact smoke](results/call-slot-smoke-01/assessment.md) passes
20 commands: eight successes and twelve exact short-budget failures. Folded
counts/profiles match exactly; random token paths each reconcile their own counts.
A/A staging qualification passes four key routes and two changed-guard rejections.
Its brief lock admission rejection is preserved; no process was signalled.

Both A/A controls complete and verify 168 commands and 84 artifacts in total.
The fixed wall envelopes are 1.6215% folded and 2.0353% token. The candidate
folded comparison verifies and passes its 5% guard: wall ratio 0.986095, CPU
0.994460. Its 1.39% wall difference is inside the A/A envelope.

Eight completed public caches were reviewed and archived outside timers:
983,495,499 unique bytes in 353,204,322 archive bytes, with 149 external evidence
hashes verified. All archive processes are terminal; original source/results/
executed snapshots remain. A pre-review lock rejection is preserved.

The [combined guarded Call comparison](results/call-slot-primary-01/assessment.md)
verifies all four complete histories. Token wall improves 1.27%, CPU 1.12%;
its wall difference is inside the 2.04% A/A envelope and below the fixed 10%
target. Folded wall improves 1.39%, inside its 1.62% envelope. The candidate is
parked with no threshold changes or tuning retries. It is not integrated.
All supervisor/controller/workflow processes are terminal.

The [whole-call census](results/whole-call-census-05/assessment.md) now completes.
Twenty-one tests include an independent 38,416-graph initialization oracle;
both original profiles reconcile. Bounded placement selects sites responsible
for 11,839,956 folded and 50,007,778 token calls in the old profiles. Those are
opportunities, not measured removals or speedups. The earlier placement exposed
newly required clearing, so the candidate shares a bounded CFG proof between
runtime and compiler. Bound exhaustion retains initialization.

The [isolated whole-call candidate](benchmarks/experiments/whole-call-inline/PLAN.md)
is tool `46b8332d`, VM `8d016bfc`, exporter `668e7934`; the wrapper is unchanged.
It permits CompareBytes and at most one direct Call under existing body/growth
limits, excluding recursive/unknown call closures. Its [workspace qualification](results/whole-call-build-02/assessment.md)
passes 300 debug and release tests, one ignored. Eleven focused tests cover the
proof, bounds, call graph, aliases, nested calls, cold faults, profiles and budgets.
[Original-artifact smoke](results/whole-call-runtime-smoke-01/assessment.md) passes
20 commands with exact deterministic accounting and original entropy retained.

The first build's two unit-test expectation failures remain. Two old heuristic
rejections now check observable cross-block execution; original cold/alias/budget
assertions remain. A new test handles the established generic native memory
message while preserving the exact fault budget. Runtime diagnostics are unchanged.

The first fresh-export attempt stopped before compilation because the experiment
builder copied old capability metadata. [Exact capability publication](results/whole-call-capabilities-01/assessment.md)
probes the new exporter, verifies all four launcher option guards, and retains
all binary/source/ready hashes. The historical builder remains frozen; follow
[its publication procedure](benchmarks/experiments/whole-call-inline/PUBLICATION.md).

The [fresh-export smoke](results/whole-call-export-smoke-02/assessment.md) passes
both original cases with no JIT declines. Folded executes 14.08 million native
Calls, compared with 25.91 million on its original artifact. Expanded code also
adds logical instructions and native bytes; these counts do not establish a
complete-command gain. Token retains its original random inputs.

The [strict differential qualification](results/whole-call-fixtures-01/assessment.md)
passes 1,050 commands: 1,024 VM executions match fresh native outputs, and two
uncalled type/borrow errors are rejected. Root Rust and the normal launcher remain
integrated compiler `9637b0ac`; whole-call tool `46b8332d` is isolated.

Generation 01's first A/A attempt stopped at disk admission, before any benchmark
child or source edit. Its failed receipt remains. [Generation 02](benchmarks/experiments/whole-call-inline/WORKFLOWS.md)
retains the same tools, real edits, controls and space/performance gates. The
generation-02 control qualification passes all key routes, guard rejections and
unchanged downstream verification checks.
Fixed gate: token wall <=0.90, CPU <1 and gain outside fresh A/A variation;
folded wall/CPU <=1.05. Native/TLS/fre and seven held-outs precede adoption.

Three completed host-build caches are preserved and independently verified to fund those timings. The new
narrow [published-build selector](benchmarks/experiments/published-build-cache/README.md)
qualifies three exact successful builds and rejects 33 invalid identities or
metadata. It preserves source, binaries and receipts; frozen guest-cache selectors
are unchanged. Exact inventory review and commit precede each retirement. The
small completed pgrust archive batch is verified. Sixteen parked runtime workflow
caches are also preserved and verified. Across 19 archives, 6.75 GB became
2.28 GB with 47,626 files preserved and 693 external evidence hashes checked.
All archive processes are terminal. Both fresh A/A histories complete and verify:
15 edited pairs per case, 168 total commands and 84 artifact hashes. Folded's
paired wall ratio is 0.999899 with a 1.8924% envelope; token's is 1.002816 with a
3.8303% envelope. Those envelopes are fixed for the candidate comparison.

The [copy-on-write preservation procedure](benchmarks/experiments/artifact-clones/PLAN.md)
passes actual APFS independent-write, metadata and failure tests. It preserves 312 duplicate files among the 336 completed parked snapshots, retaining
every path, exact byte, mode, ownership and modification time. All eight original
workflow checks and 134 external hashes still pass. Observed free space increased
by 5.47 GB; every process is terminal. Candidate folded/token comparisons are next.

The unbounded goal remains active. Continue implementation and real edited-command
comparisons after this diagnostic. Integration and the failed budget experiment
are checkpoints, not completion of a general Rust development engine.

Exact process identities and full hashes are in `.work/continuation-state.json`.
The [preceding checkpoint](docs/history/STATE-20260911-before-root-integration.md)
preserves intermediate history, prior archive batches and their ownership rules.

## Qualified runtime and limits

The preceding runtime source `aa2f6ea` / tool `0e94d6d8` introduced resumable native calls,
persistent registers, initialized guest frames and checked bulk copies.
It passes 276 debug/release tests (one ignored), 47,004 validation commands,
245 TLS commands and 382 fre bodies (seven ignored). Its [original-baseline comparison](results/resumable-copy-original-e2e-01/assessment.md)
improves folded 21.82% and token 33.09%; both still exceed native Cargo times.
Its [seven held-outs](results/resumable-copy-heldout-recovery-01/assessment.md)
pass 588 commands, 105 pairs and 294 artifacts, within both 5% guards.
Runtime options remain explicit.

This is selected-function/body execution, not full libtest or arbitrary Rust.
Real unwinding, threads, broad OS/FFI support and fastest-available native
configuration qualification remain incomplete. No fake synchronization,
longjmp cleanup, LLVM/external guest backend or silent native fallback.
Toolchain: `nightly-2026-09-08`, rustc `cea272fa3`. The private adapter is
`.work/private/workflow-rg-aot.json`; publish aggregates only.

No subagents or independent model calls. No AWS activation or unrelated process
control. Serialize task builds/tests/benchmarks/cache work with
`.work/benchmark.lock`. Never recursively search all `.work`; preserve sources,
receipts and artifacts. Archive only reviewed, owned, completed public caches.
Do not mark the unbounded goal complete at a checkpoint.

The [full previous checkpoint](docs/history/STATE-20260911-before-compiler-cache.md)
preserves earlier experiments, parked directions, failures and source identities.
