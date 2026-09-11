# Current state — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test measurements. Every user suggestion has an
[item-by-item decision](docs/SUGGESTIONS-REVIEW-20260910.md). `suggestions.txt`
is user-owned, unchanged and intentionally untracked. Local commits are authorized;
no push was requested. Branch: `experiment/resumable-native-calls`.

## Active experiment

The [lightweight compiler wrapper](benchmarks/experiments/compiler-pipeline/LIGHTWEIGHT-WRAPPER.md)
execs ordinary rustc for unselected units and loads the heavy exporter only for
selected units. Source `b54dc6e`, tool `c341296c`; baseline tool `78e60cdd`.
Both use the same VM and ordinary JIT, matched leaf inlining and strict checking.
Resumable calls, persistent registers and native call trees/stubs are off.

Qualification passes 268 debug/release tests (one ignored), fifteen process
probes, five manifest checks, 99 launcher checks and historical-tool execution.
The two fifteen-cycle API-edit comparisons verify 360 commands and 180 artifacts:

| Workflow | Median paired wall change | CPU change |
| --- | ---: | ---: |
| [pgrust](results/lightweight-wrapper-pgrust-repeated-01/assessment.md) | −4.57% | −4.46% |
| [Nushell](results/lightweight-wrapper-nushell-repeated-01/assessment.md) | −4.24% | −1.94% |

All corresponding artifacts match. Nushell original/wrong-edit artifacts differ
across cache histories; its API-edit artifact is stable. This known discrepancy
is unresolved and does not establish semantic equivalence across histories.

The [fixed cold experiment](benchmarks/experiments/compiler-pipeline/REPEATED.md)
requires all six fresh-target histories. Original tests, wrong edits, independent
checks and source restoration remain required. Native uses eighteen jobs,
O0/incremental and default test concurrency; custom uses four jobs and prebuilt
std-MIR. Installation/downloads/std-MIR setup are excluded from cold timing.

| History | Initial order | Candidate/baseline cold wall ratio | State |
| --- | --- | ---: | --- |
| 01 | native,baseline,candidate | 1.0016210970 | verified |
| 02 | candidate,baseline,native | 0.9868934347 | verified |
| 03 | baseline,candidate,native | 1.0085092329 | verified |
| 04 | native,candidate,baseline | 0.9847329487 | verified |
| 05 | candidate,native,baseline | — | unexecuted: futility |
| 06 | baseline,native,candidate | — | unexecuted: futility |

All four histories verify twelve commands and six artifacts each. The
[futility assessment](results/lightweight-wrapper-cold-futility-01/assessment.md)
rechecks those histories and both warm comparisons. Any possible final two
ratios leave the six-sample median at least **0.9858131917**: at most **1.4187%**
improvement, below the original 5% requirement. Histories 05/06 never started.
The stopping rule was not predeclared; the amendment is explicit and the original
six-history protocol remains **incomplete**. No six-sample estimate, threshold
relaxation, wrapper retention or conditional held-out testing is claimed.

The separate four-versus-eighteen worker experiment is now the next direction.
Integration is in progress; exact current qualification receipts are recorded
in `.work/continuation-state.json`. No guest runtime or installed tool changes.

## Resource planning

[Completed batch04](results/cold-storage-batch-04/assessment.md) preserves eight
exact completed targets: 84,333 paths / 21.42 GiB unique contents in 7.21 GiB
of archives. Final receipts, inventories and all 38 distinct external evidence/
source hashes verify. Thirty-six actual archives are now complete. All payloads
were decoded and hashed before retirement. Executed snapshots and reports remain
in place. Archival ran outside benchmark timing and controlled no other work.

The [archive implementation](benchmarks/experiments/compiler-pipeline/CACHE-ARCHIVAL.md)
passes 44 rejection checks, four coordinator cases and two legacy restores.
Mode derivation passes 31 rejections and nine real targets. It preserves recorded
bytes/metadata/internal hardlinks, not future Cargo reuse behavior. Only exact
reviewed task-owned completed targets may be retired. Archive outside benchmarks;
keep query metadata, private caches, installed tools and historical evidence.
Allow at least roughly 21 GiB before each large fresh history; the per-command
guard remains eight GiB and is not a reservation against other host activity.

## Next experiment

[Historical Cargo timelines](results/compiler-cold-concurrency-01/assessment.md)
show 800 custom timed units under four jobs and CPU/wall about 3.1 during cold
commands, versus about 1.5 after edits. Native has 608 units under eighteen jobs.
Overlap does not establish CPU utilization, a ready queue or a critical path.
The [worker-count plan](benchmarks/experiments/compiler-pipeline/WORKER-COUNT-NEXT.md)
is a separate next experiment: identical tool78 in both arms, four versus eighteen
jobs, qualification followed by fixed cold/warm samples and original controls.
The wrapper histories are closed after the verified futility decision. The
worker helper's first qualification is preserved; an additional JSON namespace
serialization check now passes. Actual harness integration and project
qualification follow with identical tool78 in both arms and separate namespaces.


[Constant-history inspection](results/interface-nushell-literal-history-01/assessment.md)
finds an extra `Expected OneOf` literal and changed guest offsets after edit/revert.
The allocation HashMap is never iterated for layout. This is not proof of an
interning cause or permission for content-only deduplication. The
[bounded trace design](benchmarks/experiments/artifact-diff/CONSTANT-IDENTITY-NEXT.md)
is pending; stable allocation/relocation identity is required before function reuse.

## Existing engine and limits

The broadly compared control remains `a2a0e04` / `b2aa6efe`. Its nine-workflow
[corpus](results/native-controls-corpus-01/assessment.md) verifies 756 commands,
189 independent checks, 135 edited pairs and 378 artifacts. Native controls are
explicit; a fastest-available AOT claim still needs backend/linker qualification.

The custom resumable Call/Return + persistent-register + bulk-clear experiment
is `001065a` / `78e60cdd`. [Both primary runs](results/resumable-bulk-replication-01/assessment.md)
miss the token threshold: ratios 0.8004639304 and 0.8003441753 exceed 0.8.
Folded passes; the combined gates fail. Keep these options off by default;
no rounding, more primary replication or tiny emitter tuning to cross the gate.
Its broader checks pass 47,004 mixed commands, 245 TLS commands and 382 original
fre bodies (seven ignored). The [seven held-out cases](results/resumable-bulk-heldout-recovery-01/assessment.md)
verify 588 commands, 105 pairs and 294 artifacts with no >5% paired wall
regression. These do not waive primary failures or establish full libtest support.

Strict type/borrow checking, exact budgets, original assertions and explicit
unsupported outcomes remain required. Real unwinding, threads, broad FFI and
unfiltered full suites remain incomplete. No fake synchronization or longjmp
cleanup, LLVM/external guest backend, or silent native fallback. Native controls
and native host tools are separate from the custom guest execution path.

## Continuation rules

Exact hashes, source pins, reports and active receipts are in
`.work/continuation-state.json`. Toolchain: `nightly-2026-09-08`, rustc `cea272fa3`.
Private adapter: `.work/private/workflow-rg-aot.json`; publish aggregates only.
The [previous full checkpoint](docs/history/STATE-20260911-before-cold03.md)
preserves detailed chronology and older failures.

No subagents or independent model calls. No AWS activation or unrelated process
control. Serialize builds/tests/benchmarks/cache maintenance with
`.work/benchmark.lock`; an external user-owned cleanup may hold it, so wait.
Never recursively search all `.work`. Preserve sources, receipts and artifacts.
Do not mark the unbounded goal complete at a checkpoint.
