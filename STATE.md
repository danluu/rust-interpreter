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
| 03 | baseline,candidate,native | — | running |
| 04 | native,candidate,baseline | — | pending |
| 05 | candidate,native,baseline | — | pending |
| 06 | baseline,native,candidate | — | pending |

Active run: `lightweight-wrapper-nushell-cold-03`, supervisor **14215**, controller
**14232**, started September 11 at 08:13:25 local. Inspect terminal receipts;
do not infer liveness from saved PIDs. After success, run the workflow verifier
and `assess_wrapper_cold.py --index 3` through separate supervised commands.

Retention requires at least 5% median cold wall improvement and no unresolved
warm paired wall regression over 5%. Only then run held-out Ruff/private rg-aot/
original fre checks. Preserve all six samples; no extra trials, threshold changes
or wrapper retuning after a failure. `assess_wrapper_cold.py --all` remains
unexecuted until all six histories exist. No retention decision yet.

## Resource planning

[Completed batch02](results/cold-storage-batch-02/assessment.md) preserves eight
exact completed targets: 84,317 paths / 21.42 GiB unique contents in 7.21 GiB
of archives. Final receipts, reviewed inventories and all 38 distinct external
source/evidence hashes verify. Twenty actual archives are now complete, including
[batch01](results/cold-storage-batch-01/assessment.md). All payloads were decoded
and hashed before original-file retirement. Executed snapshots and reports stay
in place. About 23.7 GiB was free before cold03.

The [archive implementation](benchmarks/experiments/compiler-pipeline/CACHE-ARCHIVAL.md)
passes 44 rejection checks, four coordinator cases and two legacy restores.
Mode derivation passes 31 rejections and nine real targets. It preserves recorded
bytes/metadata/internal hardlinks, not future Cargo reuse behavior. Only exact
reviewed task-owned completed targets may be retired. Archive outside benchmarks;
keep query metadata, private caches, installed tools and historical evidence.
Allow at least roughly 21 GiB before each large fresh history; the per-command
guard remains eight GiB and is not a reservation against other host activity.

## Direction after the fixed comparison

[Historical Cargo timelines](results/compiler-cold-concurrency-01/assessment.md)
show 800 custom timed units under four jobs and CPU/wall about 3.1 during cold
commands, versus about 1.5 after edits. Native has 608 units under eighteen jobs.
Overlap does not establish CPU utilization, a ready queue or a critical path.
An isolated custom worker-count comparison is a useful next candidate. Freeze
one tool in both arms, qualify mode-specific job recording and predeclare cold/
warm samples before running. Do not change the active wrapper's four-job controls.

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
