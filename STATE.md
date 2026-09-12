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
executables byte-for-byte. No task build, test or benchmark is active.

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

Next investigate static argument/result slot facts across native Calls and
Returns. Start with a typed, profile-weighted census using the existing artifacts;
audit VM re-entry contracts and preserve dynamic fault order. Do not optimize
until the census identifies a material, safely removable cost. Keep all frame
initialization, exact budgets, original assertions and real host randomness.

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
