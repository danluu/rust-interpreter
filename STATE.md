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

## Current decision and next work

The normal workspace qualification reproduces all three integrated binaries and
passes 289 debug/release tests, one ignored. Root Rust source remains `5b2330c`;
normal tool key remains `9637b0ac`.

Three subsequent experiments are parked after their fixed primary gates:

| Experiment | Token wall improvement | Token A/A envelope | Decision |
| --- | ---: | ---: | --- |
| x22 budget register | 1.01% | 3.99% | Below 10%, inside A/A |
| Guarded argument slots | 1.27% | 2.04% | Below 10%, inside A/A |
| Whole-call expansion | 5.23% | 3.83% | Beyond A/A, below 10% |

The [whole-call primary comparison](results/whole-call-primary-02/assessment.md)
verifies both full A/A histories and both full candidate histories. Each phase
contains 168 commands, 30 edited pairs and 84 artifact hashes. Token CPU improves
4.98%; native/control/candidate medians are 1.999s/4.462s/4.240s. Folded wall
improves 0.56%, CPU 0.77%; medians are 1.632s/1.688s/1.680s. Its wall difference
is inside the 1.89% A/A envelope. All pairs and failures remain. No tuning retry,
whole-call held-outs or source integration follows the failed fixed gate.

The isolated whole-call tool is `46b8332d`, VM `8d016bfc`, exporter `668e7934`;
wrapper unchanged. It passes 300 debug/release tests, one ignored, 20 original-
artifact smoke commands, both original fresh exports, and 1,050 strict differential
commands (1,024 VM/native comparisons, two uncalled type/borrow rejections).
Its first build's unit expectation failures, capability admission failure and
first timing's disk admission failure remain preserved. The latter launched no
benchmark child and edited no source; generation 02 retained all original gates.
Follow [exact publication](benchmarks/experiments/whole-call-inline/PUBLICATION.md)
if reproducing the frozen experimental builder.

The [recorded stage analysis](results/whole-call-costs-01/assessment.md) shows
paired token execution −291.9 ms, Cargo +62.7 ms; folded execution −26.2 ms,
Cargo +12.9 ms. Stage medians are descriptive and need not add to command medians.
No causal attribution or gate change follows from these observations.

The [typed scalar boundary census](results/scalar-boundary-census-01/assessment.md)
now passes. Diagnostic exporter `93c13c08` passes 45 exporter checks and preserves
both original guest artifacts and all original assertions; its VM/wrapper are
unchanged. Five typed-join tests pass. Both original profiles reconcile exactly,
with 3,335 folded and 14,852 token boundary rows and no exhausted analysis bounds.
The first export's wrong ABI-offset assumption failed closed; the revised observer
follows certified aggregate relocation before checking final function IDs/hashes.

Token's MIR-eligible scalars account for 88.54M direct argument copies and 47.67M
result returns. An entry-load/return-store change keeps those boundary copies.
The [final address admission](results/scalar-boundary-admission-01/assessment.md)
passes eleven tests using the actual scalar transform. It admits 453 folded and
1,542 token slots, covering 85.80M token argument copies and 47.66M scalar returns;
neither work bound is exhausted. Counts do not forecast latency.

The [scalar artifact contract](results/scalar-abi-artifact-build-01/assessment.md)
is implemented in an isolated tree and passes 297 debug/release workspace tests,
one ignored. Both original version-5 artifacts roundtrip byte-for-byte. Version 6
uses a companion ABI table; existing Program execution APIs reject scalar bodies.
The [custom interpreter](results/scalar-abi-interpreter-build-01/assessment.md) now
passes 305 debug/release tests (one ignored), including recursion, TLS, faults
and exact budgets. [Serialized CLI checks](results/scalar-abi-cli-01/assessment.md)
pass 23 commands with native Rust controls. The [custom native ABI](results/scalar-abi-native-build-03/assessment.md)
now passes 310 debug/release tests (one ignored), with actual hot native calls,
per-PC profiles and every budget boundary. [Native CLI qualification](results/scalar-abi-native-cli-01/assessment.md)
passes 64 commands and requires generated execution in all four JIT modes.
[Caller value operands](results/scalar-value-calls-build-02/assessment.md) now pass
319 debug/release tests (one ignored): all 80 width/storage combinations, hot
native transitions, recursion, mixed calls and TLS. No runtime was published.
[Typed compiler promotion](results/scalar-value-compiler-build-02/assessment.md)
now passes 334 debug/release tests, one ignored, using tool `aa56492e`.
The pass preserves typed identities through validated relocation and proves
final caller value operands after existing optimization. The first run's
oversized-input test error remains preserved. Real Rust export and Cargo
publication qualification are in progress, before any scalar timing.
The [contract and fresh complete-command gates](benchmarks/experiments/scalar-value-abi/CONTRACT.md)
remain required. Existing native Calls already cross guest frames without
returning to the Rust VM. No scalar performance comparison has run yet.

## Evidence storage and ownership

[Scalar debug preservation](results/scalar-debug-cache-01/assessment.md) retains
five completed targets: 3.47 GB in 1.05 GB of verified archives, 25,100 files and
851 external hashes checked. Source, release tools and benchmark artifacts stay
in place. The initial busy-lock attempt exited without touching any cache.

[Completed cache preservation](results/parked-runtime-cache-01/assessment.md)
verifies 19 archives: 6.75 GB of original caches in 2.28 GB of archives, 47,626
files preserved, 693 external hashes checked. All inventories were reviewed and
committed before retirement. Source, binaries, reports and executed snapshots
remain. Shared guest-cache selectors are unchanged.

[APFS copy-on-write preservation](results/artifact-clones-parked-01/assessment.md)
keeps all 336 parked public snapshots at the same paths, with identical bytes,
modes, ownership and modification times. 312 duplicates are independent clones;
all eight original workflow verifications and 134 external hashes still pass.
Observed free space increased 5.47 GB. Clone file identity/change/birth times can
differ. Actual fixtures verify independent writes and failure before replacement.
No benchmark overlapped storage work. No private data or unrelated processes were
changed. All storage supervisors, controllers and children are terminal.
Current compiler/frontend process state is recorded in `.work/continuation-state.json`.

The unbounded goal remains active. Next work follows the typed census plan;
this is a checkpoint, not completion of a general Rust development engine.
Every suggestion has an [explicit disposition](docs/SUGGESTIONS-REVIEW-20260910.md).
`suggestions.txt` stays user-owned, unchanged and untracked. Local commits are
authorized; no push. No subagents or independent model calls.

Exact full hashes and completed process identities are retained in the reports
and `.work/continuation-state.json`. The [preceding checkpoint](docs/history/STATE-20260911-before-whole-call-decision.md)
preserves intermediate census, qualification, timing and storage history.

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
