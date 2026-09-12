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

Ruff stopped at its pre-command 8 GiB disk guard after one complete cycle.
The [stop audit](results/aggregate-relocation-ruff-stop-01/assessment.md) verifies
21 primary commands, seven checks, five edit pairs and 14 artifacts, with source
restored. These partial pairs are excluded from performance gates. The original
failure and the first assessor's schema error are preserved. The single fresh retry is now running under
`aggregate-relocation-heldout-01-ruff-retry-01` (supervisor 52822).

The [declared retry](benchmarks/experiments/aggregate-byte-writes/HELDOUT-RETRY-NEXT.md)
keeps all three cycles, tools, assertions and gates. Its separate coordinator and
receipt adapter pass two original command-template checks, 30 rejection fixtures
and two monitor lifecycle/error checks. The first flag-suffix qualification
failure is preserved. Admission passed at 24.33 GiB against 24.16 GiB required;
five-second read-only space logging is active.
The failed history and frozen original verifier sources remain unchanged.

The [fourth batch](results/aggregate-relocation-space-04/assessment.md) archived
the completed new Nushell comparison: 13,455,530,886 unique bytes preserved in
4,355,839,039 archive bytes. All four terminal receipts and 99 external hashes
verify. Source, reports, tool installations and executed snapshots remain.

1. Wait for the Ruff retry controller and supervisor to finish; preserve failures.
2. Reverify through `report_heldout_recovery.collect_recovered`, then admit Nushell
   and launch `run_heldout_recovery.py --case nushell`.
3. Complete Nushell and the remaining fixed cases. Reverify all seven complete
   histories with the explicit retry mapping before any adoption decision.

The fifth archive batch preserves a completed debug-check cache: 781,927,676
unique bytes in 237,598,021 archive bytes, with 135 external hashes verified.
No installed tool or source was retired.

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
