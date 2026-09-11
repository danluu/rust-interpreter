# Current state — September 11, 2026

The unbounded goal remains active: improve the custom Rust development engine
using real source-edit/build/test measurements. Every user suggestion has an
[item-by-item decision](docs/SUGGESTIONS-REVIEW-20260910.md). `suggestions.txt`
is user-owned, unchanged and intentionally untracked. Local commits are authorized;
no push was requested. Branch: `experiment/resumable-native-calls`.

## Active direction

The allocation-history investigation now has a [small incremental-on/off
reproducer](results/allocation-history-reduction-02/assessment.md) and a
[built-MIR observer](results/allocation-history-mir-dumps-02/assessment.md).
Both pass 133 command checks; the observer preserves all eight uninstrumented
artifacts. Only the API-dependent body rebuilds where its literal allocation
splits. This explains the history sensitivity without licensing content-only
deduplication or session-local cache keys. Commits be16330 and acb0565 preserve
the two stages.

Return to compute-heavy guest execution next. Function reuse remains a design
problem, but Nu's ~71-ms lowering interval inside ~5.3-second edited commands
does not justify it as the immediate speed project. Fresh exact-code profiles
of tool78's existing bulk/resumable/persistent mode have completed. The
[qualified analyzer](results/resumable-bulk-profile-tools-01/assessment.md)
now recognizes the bulk loop without changing six historical profiles.
[Token](results/resumable-bulk-token-sample-01/assessment.md) shows 15.59%
native-boundary self samples and 9.55% clearing; [folded](results/resumable-bulk-folded-sample-01/assessment.md)
shows 40.07% clearing and 0.20% native boundaries. The [exact operation counts](results/resumable-bulk-token-transitions-01/assessment.md)
attribute 88.19% of token's interpreted operations to fixed/dynamic copies.

Source `aa2f6ea` / tool `0e94d6d8` keeps these checked transfers inside resumable
regions. [Debug](results/resumable-copy-debug-02/assessment.md) and
[release](results/resumable-copy-release-01/assessment.md) pass 276 tests, one
ignored. [Original artifact smokes](results/resumable-copy-real-smoke-01/assessment.md)
pass with zero interpreted copies and no JIT declines; token native entries
fall to ~2.65 million. These instrumented counts are not speed measurements.
The [plan](benchmarks/experiments/resumable-native-calls/COPY-TRANSITIONS-NEXT.md)
requires a new ≥10% token E2E gain and lower CPU, with ≤5% folded regression.
Baseline `e965f566` has tool78's exact VM and the candidate's exact exporter/
wrapper, isolating the runtime change. New baseline runtime flags pass CLI and
historical receipt checks; [actual pgrust qualification](results/resumable-copy-harness-01/assessment.md)
passes 36 commands and 18 matching artifacts with original assertions and source
restoration. The [two-workflow primary](results/resumable-copy-e2e-01/assessment.md)
now passes: token paired wall −15.14%, child CPU −15.28%; folded +1.06%/+0.54%
passes both 5% guards. Verification covers 168 commands, 30 edited pairs and
84 artifacts. Token median is 5.116s → 4.329s, still above native's 2.036s.
The [original b2 comparison](results/resumable-copy-original-e2e-01/assessment.md)
also passes: folded paired wall −21.82% / CPU −21.95%; token wall −33.09% /
CPU −33.29%. All 168 commands, 30 pairs and 84 artifacts verify. Candidate
medians remain slower than native: 1.913s vs 1.653s folded, 4.418s vs 2.012s token.
The first [fresh native run](results/resumable-copy-native-01/assessment.md) passes
its 23,502-command default mode, then its coordinator fails on an unused wrapper
manifest entry. The [coordinator correction](results/resumable-copy-execution-driver-01/assessment.md)
passes historical/staging checks, three positive provenance configurations and
twelve rejection cases. The [fresh full native run](results/resumable-copy-native-02/assessment.md)
now passes all 47,004 commands across both modes, including 22,238 JIT and 22,238
interpreter invocations, with no declines. [TLS/destructor qualification](results/resumable-copy-tls-01/assessment.md)
also passes 245 commands. [Fresh fre replay](results/resumable-copy-fre-01/assessment.md)
passes 382 bodies, seven ignored, with 382 fresh native executions, all 382
compared artifacts unchanged and no declines. These remain body replays, not
unfiltered libtest. The seven held-out edit workflows remain before retention.
No default change.

The [fixed seven-case held-out plan](benchmarks/experiments/resumable-native-calls/HELDOUT-STORAGE-NEXT.md)
uses separate fresh histories so reviewed public caches can be archived between
cases. Its [actual pgrust qualification](results/resumable-copy-heldout-qualification-01/assessment.md)
passes 84 commands, fifteen pairs and 42 artifacts. The gate helper preserves
both recent primary receipts and the earlier near-miss failures, and rejects
39 invalid configurations. All seven cases remain required.

The original Nushell type-relations history [stopped at the space guard](results/resumable-copy-heldout-01-case-01-stop/assessment.md)
after five primary commands and one check, with zero successful-edit pairs.
Its original assertions, wrong-edit failures, four snapshots and restored source
verify. The admission estimate had omitted the 8 GiB running reserve. The
[corrected calculation](results/workflow-space-floor-01/assessment.md) rejects
that admission and requires 25.99 GiB. The [qualified retry amendment](benchmarks/experiments/resumable-native-calls/COPY-HELDOUTS-RETRY-01.json)
changes only this case's run ID; it preserves the original failure, remaining
case order, controls and gates. Its [qualification](results/copy-heldout-retry-gates-01/assessment.md)
rejects 29 invalid inputs and reproduces both primary receipts.

Fresh case01 retry `resumable-copy-heldout-01-case-01-retry-01` is running under
supervisor 52502, corpus controller 52514 and workflow controller 52525, started
September 11 at 14:26:25 local. Its [admission](results/resumable-copy-heldout-01-case-01-retry-01-preflight/summary.json)
observed 30.34 GiB free and preceded corpus startup by 0.169 seconds. Runtime,
benchmark and gate sources remain frozen. Finish its partial gate verification,
then continue Ruff, Nushell, forward-anchored TLS, pgrust SHA-1, pgrust and private
rg-aot in the recorded order. Use the amended aggregate evaluator after all
seven complete. No subset authorizes retention.

Storage maintenance has verified 205 archives. Recent batches include
[eight recovered histories' caches](results/heldout-recovery-storage-01/assessment.md),
[four stopped-history caches](results/copy-stopped-storage-01/assessment.md) and
[twenty legacy native targets](results/legacy-native-storage-01/assessment.md).
Every archive preserves original reports and executed artifacts; private caches
remain excluded. [Eight additional artifact histories](results/copy-artifact-clones-01/assessment.md)
retain all snapshot paths through independently writable clones. The
[standalone selector](results/standalone-clone-inputs-01/assessment.md) is qualified
but has not been used to modify snapshots. These are storage operations outside
benchmark timers, with no compilation-speed claim.

## Closed worker-count experiment

The [worker plan](benchmarks/experiments/compiler-pipeline/WORKER-COUNT-NEXT.md)
compares four versus eighteen Cargo workers using identical tool **78e60cdd**
in both arms. Ordinary JIT and leaf inlining are matched; resumable/persistent/
tree/stub options are off. Native/check retain eighteen jobs, O0/incremental
and default test concurrency. No guest runtime or installed binary changed.

Source **2c86d1f** integrates independent custom counts in the workflow/corpus
CLIs and receipts. [Harness qualification](results/worker-count-harness-02/assessment.md)
reverifies seventeen histories (1,524 commands / 762 artifacts), rejects two
false worker receipts and eighteen invalid CLI cases, and tests two actual late
guard paths. [Helper02](results/worker-count-helper-02/assessment.md) covers JSON
namespace serialization; [archive07](results/cache-archive-qualification-07/assessment.md)
passes 44 rejections, four coordinator cases and both older formats.

The first pgrust attempt was [rejected before compilation](results/worker-count-pgrust-rejection-01/assessment.md)
by the old same-tool guard. Its corrected [three-cycle qualification](results/worker-count-pgrust-qualification-02/assessment.md)
passes 36 commands, eighteen matching artifacts, eleven frozen inputs/eighteen
wrapper traces and exact source restoration. Paired wall ratio **1.0055983071**;
qualification timings are excluded from adoption measurements.

[Nushell qualification](results/worker-count-nushell-qualification-01/assessment.md)
passes twelve commands, six artifacts and exact tool/configuration/source checks.
Cold wall is **61.125s at four workers / 30.550s at eighteen**; child CPU is
**178.047s / 233.596s**. This ~50% latency reduction costs ~31% more child CPU
in one excluded qualification. API-edit wall is 4.972s / 4.957s. Keep the planned
CPU guard and all observations; no adoption follows from this pilot.

The [corpus qualification](results/worker-count-corpus-qualification-01/assessment.md)
completed 84 commands and 42 artifacts, verifying JSON receipts and actual
four/eighteen-job forwarding. Its timings are excluded from primary statistics.

The [fifteen-cycle pgrust primary comparison](results/worker-count-pgrust-repeated-01/assessment.md)
verifies 180 commands, ninety artifacts, eleven frozen inputs and source
restoration. Median paired wall ratio is **0.9981098106** and child-CPU ratio
**0.9996062101**: no material worker-count gain, with warm guards passing.

The [fifteen-cycle Nushell primary comparison](results/worker-count-nushell-repeated-01/assessment.md)
completed and verifies 180 commands/ninety artifacts, eleven frozen inputs,
exact tools/options and source restoration. Median paired wall ratio
**1.0059031510** and CPU ratio **1.0732865843** pass both warm guards but show
no warm-build gain. Original/wrong-edit artifacts repeat the known cross-cycle
layout difference; corresponding modes match and the API-edit artifact is stable.
Reported lowering is about 71 ms within roughly 5.3-second edited commands.

Both warm primaries and four fixed cold histories completed and verified.
The [four-history decision](results/worker-count-cold-decision-through-04/assessment.md)
stops the unstarted fifth and sixth histories under the predeclared failure rule.
Even the best possible final CPU median is **1.2724474026**, above the 1.1 guard.
The six-history protocol is explicitly incomplete; no adoption/default change.
Cold wall falls about 45–51% in the observed runs, while child CPU rises 24–52%.
Warm primary latency shows no material benefit. Exact observations and source
restoration are preserved, including [cold04](results/worker-count-nushell-cold-04/assessment.md).

The worker experiment is closed. Its eleven inputs remained unchanged through
the decision; Git e4bbffb preserves the tracked source versions. The launcher
was released for the now-qualified allocation-origin diagnostic.
The original/wrong/API/restored Nushell history and small reduction are complete.
Guest code and runtime defaults remain unchanged.

The [latest 32-cache batch](results/worker-cold-storage-batch-05/assessment.md)
completed and verified. The [four cold04 caches](results/allocation-history-storage-01/assessment.md)
also verified. The [eight copy-comparison caches](results/copy-comparison-storage-01/assessment.md)
and the [eight original-comparison caches](results/copy-qualification-storage-01/assessment.md)
plus the [eight recovered Nushell/Ruff caches](results/heldout-recovery-storage-01/assessment.md)
bring the total to 181 archives (160 workflow and 21 host). The new
[artifact clone qualification](benchmarks/experiments/compiler-pipeline/ARTIFACT-CLONES.md)
preserves independent write behavior and rejects 18 invalid/failure cases.
The [pilot](results/artifact-clone-pilot-01/assessment.md) and
[six-history batch](results/artifact-clone-storage-batch-01/assessment.md)
retain all 294 executed snapshot paths, bytes and checked metadata while sharing
data for 203 duplicates. All seven original workflow verifications reproduce.
This maintenance is outside benchmark timers; it is not a compilation gain.

The earlier [warm-cache recovery](results/warm-storage-batch-01-recovery-01/assessment.md)
preserves its original lock-scheduling failure and completed recovery receipts.
Never queue another lock waiter during an archive batch.

Worker retention requires at least 10% median cold wall reduction, no >5% warm
wall regression and no >10% child-CPU increase for the checked primary groups.
The plan now predeclares deterministic futility stopping only for failure bounds,
with incomplete protocols identified; no early acceptance or extra trials.
Conditional held-out checks remain required before any adoption claim.

## Closed wrapper experiment

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


## Resource planning

The next storage operation is inventory preparation for
`.work/cache-batches/worker-cold-storage-batch-05.json`: 32 exact completed
public targets, including cold03 and earlier fre comparisons. Review and commit
its inventories before application; no competing lock waiter during the batch.
Cold04 remains unstarted. Current completed archive count is 121.

The [latest eight-target selection](results/worker-cold-storage-batch-03/assessment.md)
completed seven archives before a shared-volume space drop rejected the final
child at preflight. Its original files were untouched. The [separate recovery](results/worker-cold-storage-batch-03-recovery-01/assessment.md)
archives that final target and verifies its evidence; the original failed batch
stays incomplete. That recovery brought completed archives to **89** (68 workflow, 21 host).
Available space briefly fell to about 636 MiB, then recovered to about 19 GiB
without process intervention. The cause is unknown. Do not weaken the guards.

The [32-target fre batch](results/worker-cold-storage-batch-04/assessment.md)
is now complete and verified: 56,584 paths, 407 external evidence hashes,
all original payloads preserved. Completed archives now total **121**
(100 workflow, 21 host). About 23.7 GiB was free afterward. Cold03 subsequently completed; prepare
space for cold04 with all eleven worker inputs still frozen.


The [completed twenty-four-target batch](results/worker-cold-storage-batch-02/assessment.md)
preserves the first cold history's four Cargo targets and twenty completed debug
host caches: 64,858 paths / 16.77 GiB unique contents in 5.70 GiB of archives.
All 2,150 external evidence hashes verify. That batch brought completed archives to 81
(sixty workflow targets and 21 host targets); the newer total is 89 above. The host reported about 23 GiB
free afterward. Cold02 is complete; prepare space for cold03 next.

The [host selector](results/host-cache-selector-03/assessment.md) and archive
regression checks pass, as does the [actual pilot](results/host-cache-pilot-01/assessment.md).
Only completed default-debug checks without installed-tool publication qualify;
all external qualification evidence remains outside retired targets.

The [completed twelve-target batch](results/worker-cold-storage-combined-01/assessment.md)
preserves worker Nushell and older Nushell/Ruff corpus caches: 249,643 paths /
19.16 GiB unique contents in 5.72 GiB of archives. All terminal receipts and
207 distinct source/evidence hashes verify. That batch brought completed archives to 56; the newer total is 81 above.
the host reported about 21 GiB free afterward. The old unapplied Ruff object-only
inventory is obsolete because its exact target has now been archived.


[Completed batch04](results/cold-storage-batch-04/assessment.md) preserves eight
exact completed targets: 84,333 paths / 21.42 GiB unique contents in 7.21 GiB
of archives. Final receipts, inventories and all 38 distinct external evidence/
source hashes verify. That batch brought the archive count to thirty-six; the current total is
eighty-nine after the separately reviewed storage work above. All payloads
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

## Evidence for next directions

[Historical Cargo timelines](results/compiler-cold-concurrency-01/assessment.md)
show 800 custom timed units under four jobs and CPU/wall about 3.1 when cold,
versus about 1.5 after edits. Native has 608 units under eighteen jobs. Overlap
is not CPU utilization, a ready queue or a critical-path proof. This motivated
the now-closed isolated worker comparison.

[Constant-history inspection](results/interface-nushell-literal-history-01/assessment.md)
finds an extra `Expected OneOf` literal and changed guest offsets after edit/revert.
The allocation HashMap is never iterated for layout. This is not proof of an
interning cause or permission for content-only deduplication. The
[bounded trace](benchmarks/experiments/artifact-diff/CONSTANT-IDENTITY-NEXT.md)
is qualified on fixtures and the completed large history. Stable allocation/
relocation identity is required before function reuse.

The opt-in allocation trace is implemented in the exporter and a tracked
[fixture qualification driver](benchmarks/experiments/artifact-diff/check_allocation_trace.py).
It captures initialized bytes, full instance kinds and relocation origins, with
bounded output and an artifact-hash footer. Four new Rust boundary tests and
original-fixture differential checks are written. The [debug workspace check](results/allocation-trace-debug-01/assessment.md)
and [release check](results/allocation-trace-release-01/assessment.md) pass all
272 tests, one existing ignored. [All 383 original-fixture commands](results/allocation-trace-fixtures-01/assessment.md)
pass with byte-identical baseline/disabled/enabled artifacts. Tool `e965f566`
changes only the exporter; VM and wrapper hashes match their previous versions.
The completed worker measurements used unchanged installed tool78.
The launcher now exposes explicit allocation tracing. Its [17-command qualification](results/allocation-trace-launcher-02/assessment.md)
and [99-check original regression](results/allocation-trace-launcher-regression-01/assessment.md)
pass, including historical-tool execution. The [large-project history](results/allocation-trace-nushell-history-01/assessment.md)
now passes eight native/custom commands and preserves four complete traces.
Function reuse is not implemented. See the [draft details](benchmarks/experiments/artifact-diff/CONSTANT-IDENTITY-NEXT.md).

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

The [qualified origin inspector](results/allocation-origin-queries-02/assessment.md)
can join exact initialized allocation contents to all request ancestry and full
function context. It preserves distinct mutable TLS identities and checks exact
serialized output bounds. The [actual Nushell attribution](results/allocation-origin-nushell-history-01/assessment.md)
finds the literal split already present in compiler allocation IDs after the API
edit and revert. All four artifacts match historical bytes. The small incremental-on/off
reduction and its byte-preserving MIR observer reproduce selective rebuilding;
no content-only deduplication or cache adoption.

The [allocation transport helper](results/allocation-trace-transport-01/assessment.md)
passes four real traces and 33 malformed-file checks with exact byte/event
boundaries. It checks the selected artifact hash before use; deeper origin
semantics remain in the qualified inspector. Launcher integration and the traced Nushell history are qualified.
No performance claim follows.
