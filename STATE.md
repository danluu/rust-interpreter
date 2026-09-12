# Current state — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test benchmarks. Every item in `suggestions.txt`
has an [explicit decision](docs/SUGGESTIONS-REVIEW-20260910.md); that user-owned
file remains unchanged and untracked. Local commits are authorized; no push.
Branch: `experiment/resumable-native-calls`.

## Current experiment

The isolated aggregate-frame relocation exporter is tool `9637b0ac`, built from
the current `0e94d6d8` source with [tracked injection recipes](benchmarks/experiments/aggregate-byte-writes/build_relocation.py).
It reuses storage for nonoverlapping MIR locals with emitted-byte write proofs,
normal-return edge handling, named origins, and checked ABI/scratch relocation.
All VM initialization remains. VM and wrapper binaries are unchanged.
The production compiler has not adopted this experiment.

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

The first of seven held-outs, [Nushell type-relations](results/aggregate-relocation-heldout-01-nushell-type-relations/relocation-assessment.md),
passes: wall +1.10%, CPU +1.14%; native/control/candidate medians
7.529s/4.051s/4.066s. All 84 commands, 15 edited pairs and 42 artifacts verify.
Remaining order: Ruff, Nushell, fre forward/TLS, pgrust SHA-1, pgrust, private
rg-aot. Every case must stay within 5% paired wall and CPU regression.
Keep failures; do not adjust gates or pool cases to hide a regression.

Recorded [capture/finalization costs](results/aggregate-relocation-pass-costs-01/assessment.md)
are 41.9 ms folded and 189.5 ms token. Token execution saves only 79.3 ms paired,
against 237.4 ms more Cargo time. These are completed-run observations, with
other pass effects and shared-host noise; the components do not prove causation.

## Immediate continuation

Ruff is running as `aggregate-relocation-heldout-01-ruff`. Its live admission
passed with 22.01 GiB free against 16.16 GiB required. Four completed public
archive batches are committed. The new
[compiler-comparison cache selector](results/compiler-cache-selector-03/assessment.md)
qualifies four real identities, 25 selector rejections, a restore fixture,
27 batch-routing rejections and 44 archive regressions. Two qualification
failures and their source snapshots are preserved. Existing measured verifier
sources remain unchanged.

The [fourth batch](results/aggregate-relocation-space-04/assessment.md) archived
the completed new Nushell comparison: 13,455,530,886 unique bytes preserved in
4,355,839,039 archive bytes. All four terminal receipts and 99 external hashes
verify. Source, reports, tool installations and executed snapshots remain.

1. Wait for the Ruff workflow and supervisor to finish; keep measured sources
   frozen. Inspect `.work/experiments/aggregate-relocation-heldout-01-ruff/status.json`
   and its `relocation-assessment.json` when complete.
2. Recheck live Nushell admission using `heldout_space.estimate`. Only then
   launch supervised `run_heldout.py --case nushell` from `aggregate-byte-writes`.
3. Complete the fixed remaining cases under the [qualification plan](benchmarks/experiments/aggregate-byte-writes/QUALIFICATION-NEXT.md).
   The [qualified final reporter](benchmarks/experiments/aggregate-byte-writes/report_heldouts.py)
   independently reverifies all seven histories. No adoption before that result.

Exact process identities, full tool hashes and current receipts are in
`.work/continuation-state.json`; inspect live receipts after a restart.

## Qualified runtime and limits

Current runtime source `aa2f6ea` / tool `0e94d6d8` retains resumable native calls,
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
