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

The compiler experiment has completed primary, broad correctness and all seven
held-out gates. The exact candidate is still isolated; source integration and
production adoption have not been performed.

The [six fresh profile executions](results/aggregate-relocation-profiles-assessment-01/summary.json)
verify against the exact original-source benchmark artifacts and their own
emitted code. Clearing is 20.42% of folded and 10.10% of token self samples.
The [cursor census](results/aggregate-relocation-cursor-census-02/assessment.md)
reconciles all 1,304 cursor samples. Remaining-budget loads/stores alone account
for 7.54% folded and 10.06% token. No new guest execution was needed for the split.
The first census was rejected at the lock; its failure/source are preserved.

The next implementation is declared in
[BUDGET-REGISTER-NEXT.md](benchmarks/experiments/aggregate-byte-writes/BUDGET-REGISTER-NEXT.md):
reserve x22 for the exact remaining budget across resumable native chains.
Call temporaries must be reassigned with a clobber audit; Return's private-frame
register-base load moves after the checked result copy. The external prologue
loads budget before the internal resume label; every VM exit publishes it before
restoring the host register. Preserve all three persistent guest-register pairs,
checks, counts, initialization and non-resumable modes.

The [isolated budget-register build](results/budget-register-build-02/assessment.md)
now passes 293 debug and release workspace tests, one ignored. Tool `36656766`
contains VM `d0eb1143`; exporter and wrapper bytes match control `9637b0ac`.
Focused cases cover every budget, faults, profiles and large register/ABI copies.
Build 01's test-message mismatch remains preserved; runtime error behavior did
not change. The implementation is committed and production sources are unchanged.

The [native validator](results/budget-register-native-01/assessment.md) passes
47,004 commands. The [original-artifact smoke](results/budget-register-smoke-05/assessment.md)
passes 20 commands, and the TLS/destructor suite passes 245 commands. All original
assertions and runtime limits remain.

Smoke 01's incorrect expected error literal and lock rejections 02/03 are
preserved. Smoke 04 exposed an invalid cross-process determinism assumption:
token uses actual host entropy. An [unchanged-VM repetition](results/budget-register-randomness-01/assessment.md)
confirms varying paths while all profiles account exactly for their own totals.
Smoke 05 preserves randomness, checks per-run accounting, and retains exact
cross-run counts for deterministic folded-trie. Performance gates are unchanged.

The [full fre qualification](results/budget-register-fre-01/assessment.md) passes
382 bodies, seven ignored, with 382 fresh native controls and identical exported
artifacts. No outcome changes or JIT declines. Broad correctness is complete.

The [folded A/A control](results/budget-register-aa-01-folded-literal-trie/budget-assessment.md)
completed and verifies 63 primary commands, 21 Cargo checks and 42 paired
artifacts. Paired wall ratio is 1.001141, CPU 1.001477; the prescribed wall
variation envelope is 2.4477%. Cross-cycle allocation/layout differences remain
visible, while corresponding baseline/candidate artifacts are identical.

The [token A/A control](results/budget-register-aa-01-token-phrase/budget-assessment.md)
also completes: paired wall ratio 0.999931, CPU 0.994515; its fixed wall envelope
is 3.9943%. All 84 commands and 42 artifacts verify.

The [candidate folded comparison](results/budget-register-e2e-01-folded-literal-trie/budget-assessment.md)
passes its regression guard: wall ratio 0.988390, CPU 0.981421. The 1.16% wall
difference lies within folded's A/A envelope; it is not an established speedup.
Native/control/candidate medians are 1.745s / 1.786s / 1.776s.

The candidate token comparison `budget-register-e2e-01-token-phrase` is active
(supervisor 77782). Keep its frozen driver/harness/helper files unchanged and
wait for the workflow, controller and supervisor to finish before another user
of the benchmark lock. Candidate token's fixed gate remains at least 10% wall
improvement, lower CPU and a gain exceeding its 3.9943% A/A envelope.

Next actions:
1. Finish and verify the active token comparison; preserve all pairs and failures.
2. Run `report_budget_primary.py` through supervisor with ID
   `budget-register-primary-01`. It recomputes all four cases, checks receipt
   order and source/component identity, and reports complete-command stage medians.
3. If primary gates fail, park this ABI without tuning variants and select a
   larger direction using the completed evidence. If they pass, all seven
   separate held-out guards remain required before adoption.
4. Source integration of qualified components is a separate reproducible step.

The unbounded goal remains active. Broad correctness is complete; the combined
candidate performance decision is still pending.

Five committed archive batches preserve completed public Cargo caches.
The newest preserves a debug-check target: 781,927,676 unique bytes in
237,598,021 archive bytes, with 135 external hashes verified. No installed tool,
source, result or executed artifact snapshot was retired.

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
