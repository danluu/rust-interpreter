# Review of suggestions.txt

Reviewed against retained engine `57a54edd`, the implementation, the original
[plan](../PLAN.md), the [five persona rounds](../persona-reviews.md), and the
recorded experiments. The review is useful, but its claims and proposed speedups
are hypotheses until checked. The source review is user-owned and remains intact.

## Direction and decisions

The immediate order is measurement controls, JIT decline correctness, a concise
current status, then a larger native-call experiment. Small emitter optimizations
are no longer the default direction. Native Cargo remains an explicit comparison;
the requested engine continues to use our own interpreter and emitter.

The original plan started with native artifact caching. That experiment was done:
the [native-cache results](../RESULTS.md) did not demonstrate a consistent warm
edit benefit. The user then explicitly requested a custom interpreter/JIT and
rejected unchanged builds as the main success metric. This explains the change
of backend and priority. It does **not** waive the original requirements for
correct reuse, strong native controls, repeated real edits, compatibility, or
complete-command performance. Those remain unfinished engineering work. An
experimental runtime improvement is not qualification for large-project use.

“Never loses” tiering is not a defensible promise. Previous runtime can choose
poorly after an edit; building a native test may compile a whole target; mixed
selection can pay both export and native compilation. A future opt-in hybrid
must include that work, unavailable histories, and changing workloads in its
measurements. Substituting an existing JIT library would conflict with the
user's custom-backend instruction, independent of any Cranelift platform bug.

## Item-by-item disposition

**0 — Overall verdict.** Accept the direction, qualify the numbers. Selected
frontend/link dominated batches and compute-heavy batches must be reported
separately. Ratios describe the pinned controls on this host. The latest profile
is [sample 04](../results/retained-token-cpu-sample-04/summary.md), not sample 03.
Heterogeneous pair counts are bookkeeping, not an adoption result.

| Item | Decision and reason |
| --- | --- |
| 1.1 Emitter treadmill | Accept. Use the observed call/dispatch cost to choose a larger experiment; stop treating small paired savings as progress toward native parity by themselves. |
| 1.2 Per-test native tiering | Defer as an explicit hybrid comparison. It cannot guarantee native latency and must not silently replace the requested custom backend. Model compilation granularity and double work first. |
| 1.3 Export once, select later | Accept the selection invalidation problem. Design a shared graph with multiple entry descriptors; eagerly lowering every test can increase work and encounter unsupported bodies unnecessarily. Measure selection separately from real edits. |
| 1.4 Function bytecode reuse | Accept direction, reject the proposed key as sufficient. Include compiler/target/layout/ABI/features/lowering options, semantic dependencies, stable identities and relocations. A crate hash alone also invalidates all local functions after each edit. |
| 1.5 Frontend floor | Accept. Add an independent matched Cargo-check control and record export-pass timings. Wall-time subtraction between separate runs is descriptive, not causal attribution. |
| 1.6 Publication and macros | Keep publication available as an explicitly unchanged-build result; the user deprioritized it. Macro expansion remains a possible frontend direction after current control measurements. |
| 1.7 Plan deviation | Addressed above. The plan already records the custom-backend pivot; stronger statistical and compatibility gates still need work. |
| 1.8 Compatibility | Accept explicit limits and real libtest metadata. Do not implement fake pthread success or longjmp-based catch_unwind: unwinding must run Rust cleanup correctly and preserve synchronization semantics. |
| 2.1 Strong native control | Accept. Add independently configurable native profiles/jobs and matched checking. Qualify available backends/linkers on this pinned macOS toolchain before assuming the proposed flags compose or help. Stock repository settings remain a separate useful control. |
| 2.2 Workload groups | Accept. Remove the mixed N/45 headline from current documentation; retain historical raw counts. |
| 2.3 Repeats and CPU | Implemented and checked with three cycles: fifteen edited pairs, rotated mode positions, per-child CPU, per-edit spread. Corresponding engines agree; the separate cross-history identity check failed and remains documented. Add stronger repetitions/A/A before fine-grained decisions. Shared-host load is recorded; do not disrupt other work or wait indefinitely for load <1. A historical A/A range is context, not a universal significance threshold. Bootstrap intervals require an explicit treatment of correlated cycles and distinct edits. |
| 2.4 Tracked reproducer | Token case, launcher and allocation flag were already committed in `9358c2b`. The tracked corpus runner and status generator are now implemented and exercised. |
| 2.5 Realistic workloads | Accept. Existing fre body replays give broad execution evidence but are not an unfiltered libtest command. Add interface/test/macro/dependency edits and report unsupported cases as failures of coverage, not missing samples. Reverts are now explicit cycle anchors. |
| 2.6 Cold setup | Accept explicit labels. Existing measurements exclude toolchain/dependency-fetch/std-MIR setup and OS-cache clearing. Keep setup separate and visible; do not retroactively call target-cache-cold measurements installation-cold. |
| 3.1 Native calls | Highest-priority runtime direction. Begin with typed eligibility and a bounded calling convention. Native branches alone do not remove required frame initialization, argument copies, budgets, traps or TLS cleanup. Profile percentages are not predicted savings. |
| 3.2 Register allocation | Consider together with the new call ABI. The earlier fixed-register residency census addressed the existing ABI only; it does not rule out an allocator spanning loops and calls. |
| 3.3 Budget placement | Investigate with native calls. Preserve exact instruction limits and fault order, including straight-line tails; blindly moving checks to backedges changes behavior. |
| 3.4 Guarded arena | Defer pending a memory-model design. Guard pages do not enforce subpage, object, logical-budget or readonly boundaries. Pointer provenance is not currently modeled. |
| 3.5 Persistent execution preparation | Accept redundant preparation as a target. Correction: native functions are already compiled lazily at first entry. Reusable validated immutable code must be separated from fresh guest memory/TLS/allocator state. |
| 3.6 Heap fast paths | Defer behind calls: latest token sample attributes about 3.7% to heap work. Preserve allocator behavior and limits if revisited. |
| 3.7 Compact bytecode | Defer until measured decode/storage costs justify a format change. Preserve full 128-bit operations and alias semantics. |
| 3.8 Cranelift library | Decline for the requested guest engine. It can be a separately labeled native control. A cg_clif unwind failure does not establish a Cranelift-library limitation. |
| 3.9 Default JIT | Keep explicit engine selection while platform coverage and decline handling are incomplete. The interpreter remains the portable reference. Revisit launcher defaults after qualification. |
| 4.1 Tiny rustc wrapper | Confirmed heavy exporter delegates with spawn/wait. Implement a lightweight exec path in a separate, measured pipeline change; preserve Cargo jobserver, exit/signal behavior, target/sysroot selection and host tools. |
| 4.2 Duplicate publication | Confirmed two writes in strict mode. Audit direct-export/audit/capture consumers before removing the requested output. A sidecar-only wrapper mode can avoid duplication without breaking the direct interface. |
| 4.3 Shared dependency targets | Accept investigation, not unconditional sharing. Cache keys must cover compiler/target/flags/features/sysroot and selected-crate invalidation; comparisons need isolated cache histories and locks. |
| 4.4 Resolve tool proxies | Defer until process-overhead measurements. Cache resolved paths with compiler identity; retain integrity checks and invalidation on toolchain changes. |
| 4.5 Jobs option | Accept with native-control work. Keep matched settings recorded and limit our own concurrency without touching other workloads. |
| 4.6 Names/profile cost | Accept separate compact identities as a design need. Profiles format ops only when profiling. Compiler shim names can collide; names are not unique IDs, as the frame census demonstrated. |
| 5.1 Toolchain pin/identity | Accept pin and explicit wrapper compatibility diagnostics. Avoid a stable-default build failure and a cryptic mismatched rustc_driver load. |
| 5.2 Format/lint | Accept a separate formatting/qualification commit. Do not rewrite frozen measured sources mid-run or conflate source-key changes with performance. Establish a clean lint baseline before requiring it in CI. |
| 5.3 Split large functions | Accept incrementally alongside owned changes. Separate graph construction, calling convention and intrinsic lowering when those paths change; avoid a broad untested rewrite. |
| 5.4 Typed Op visitors | Accept exhaustive shared traversal, but preserve each analysis's distinctions: read-before-write order, aliases, indirect call arguments and conservative boundaries. |
| 5.5 Named AArch64 operations | Accept, starting with branch relocation/ABI work. Add encoding checks and retain differential execution tests. |
| 5.6 Structured errors | Accept stable decline/error categories first, then exporter blocker categories. A category is not permission to ignore an executed operation. |
| 5.7 Compiler items | Accept where pinned rustc supplies an appropriate lang/diagnostic item. Keep explicit errors and tests for remaining path-based matches; not every intrinsic has such an item. |
| 5.8 Exporter repeated work | Confirm and profile each path before optimizing. Index entry names/allocator presence; replace large Repeat expansion only with equivalent memory and initialization semantics. |
| 5.9 Shared configuration/schema | Accept incremental common parsing and a capability record. Keep artifact-version validation explicit and versioned. |
| 5.10 Constants | Accept named encoding/capacity limits as the owning code is revised. A named constant needs a documented invariant, not just a renamed literal. |
| 5.11 Test-only observability | No production storage cost from cfg(test) fields. Keep useful emitted-code census tests; isolate their hooks when restructuring the emitter. This is maintainability work, not a runtime fix. |
| 5.12 Python package/assertions | Accept incremental shared modules; repeat/CPU logic is now shared. Replace safety-critical asserts with explicit checks. One enormous CLI migration is unnecessary before the controls work. |
| 6.1 Codegen limits | Confirmed error propagation. Fix known encoding/capacity exhaustion to decline atomically; preserve actual internal relocation errors as errors. Add boundary and execution-equivalence checks. |
| 6.2 Pointer truncation | Do not change blindly. Memory operands currently use target-width address semantics, with tests; indirect function identities and allocator layouts use stricter contracts. Document and audit these distinctions. |
| 6.3 Tagged arena crossing | Accept as a documented provenance limitation. The engine is not an undefined-behavior detector or hostile-code sandbox. Valid Rust pointer behavior still requires differential coverage. |
| 6.4 Unsafe/ABI contract | Accept. Document pointer lengths/lifetimes, exclusive guest storage, emitter-owned entries, same-thread write protection, supported endian/platform, and make thread confinement intentional. |
| 6.5 Null prefix | Audit/document current minimum-storage behavior before changing it. Bytes 1–15 are not all guard memory under the present bytecode contract. |
| 6.6 Allocation accounting | Distinguish guest working-memory/live-allocation limits from host RSS and map metadata. Audit bad-layout versus out-of-memory outcomes against Rust allocator contracts; do not report the guest budget as a host-memory cap. |
| 6.7 MIR catch-alls | Accept targeted pinned-toolchain coverage audit. Unsupported operations must remain explicit; supporting volatile or unwind behavior requires semantics, not another name match. |
| 7.1 Random differential tests | Accept deterministic seeded valid-program generation with persisted failures. The archived suite has 47,004 mixed commands, including 22,238 JIT invocations across two modes; these are not unique cases or general randomized CFG generation. |
| 7.2 Limit/platform tests | Accept boundary/decline tests now; retain portable interpreter testing. Performance gates belong in reproducible benchmarks, not timing-sensitive unit tests. |
| 7.3 Test counts | Accept a reproducible command and aggregate clarification: library-only counts differ from all bytecode unit/integration tests. Historical snapshots keep their historical counts. |
| 7.4 Test builders | Accept a small shared builder for new generated/boundary suites. Do not obscure the concrete operations a regression exercises. |
| 7.5 Audit freshness | Publish a current coverage index and fresh reports for expanded coverage; preserve old audits as dated evidence. Lowered, executed, ignored and unsupported are separate statuses. |
| 8.1 Current-state page | Accept. Current source, measured binaries, coverage and next work need one authoritative view. |
| 8.2 Documentation structure | Accept concise README, generated status/results index, mechanism-only architecture and historical narrative links. Preserve historical report paths. |
| 8.3 Build names | Use Git commit plus eight-character tool key in new summaries. `af9aa691` and `57a54edd` have different test sources but byte-identical measured production binaries; retain both identities explicitly. |
| 8.4 Clear findings | Accept scoped ratios and limits instead of repeated generic caveats. Do not infer tuned-native performance from stock controls. |
| 8.5 Coverage qualifications | Accept explicit 150,000 allocation limit, trap/normal-try flags, 382 body passes/7 ignored, and native input × mode counts. Do not claim libtest or whole Nushell execution from lowering alone. RESULTS.md is already titled as earlier native-cache/publication work; retain its linked path. |
| 9.1 Git/state | Git and reasonable commits already exist. Fix the stale no-Git continuation rule. Keep current state concise and archive old checkpoints rather than deleting evidence. Use sidecar provenance: ready.json currently has an exact binary-hash schema and must not be changed casually. |
| 9.2 Cache cleanup | Decline blanket deletion. Clean only exact task-owned, completed compiler caches after lock/ownership/artifact/live-file checks. Preserve private caches and evidence. Consolidate reusable drivers into tracked scripts. |
| 9.3 Reconstructability | Accept a build/source index. Correction: measured af9 source and corrected 57 source are both archived and reproduced. A claim that every historical key is reconstructible needs an actual audit. |
| 9.4 Results organization | Generate a nondestructive index first. Do not relocate/delete/compress historical shards merely because the current status omits them; existing reports and other work may reference them. |
| 9.5 ICE/quarantine deletion | Decline quarantine deletion: it is outside this task's ownership. Ignored historical crash logs are not a performance blocker; preserve evidence unless exact ownership and cleanup need are established. |
| 9.6 Historical backend removal | Keep archived native controls reproducible. Consider default-members and historical documentation instead of deleting still-referenced tools. Removing experimental checking/capture modes needs a caller/fixture audit, separately from runtime work. |
| 9.7 Decision rules | Accept. Predeclare required behavior, target workloads, meaningful end-to-end gain and held-out checks. Report regressions and uncertainty; do not choose success criteria after seeing the pairs. |

The [historical command recount](../results/historical-validation-counts-01/assessment.md)
corrects the former “23,502 cases per mode” wording: each mode has 23,502 mixed
commands including 11,119 JIT and 11,119 interpreter invocations. Native builds,
batched native oracles, exports and intentional rejection checks are distinct.
Current status uses these categories; original reports remain preserved.

**10 — Proposed schedule.** Accept controls first and larger call/ABI work next.
Documentation and correctness fixes can proceed between serialized measurements.
Native tiering and eager export-all are design experiments with costs and
compatibility constraints, not guaranteed shortcuts. Calendar estimates in the
review are not commitments or evidence of feasibility.

## Implemented follow-ups

- Item 9.2 now has bounded completed-cache archival, with exact workflow and
  invocation ownership, decoded payload verification before retirement, and
  preserved query metadata and executed snapshots. [The format qualification](../results/cache-archive-qualification-06/assessment.md)
  passes 44 rejection checks, four coordinator cases and restoration of both
  earlier formats; [cache selection](../results/workflow-cache-evidence-01/assessment.md)
  passes 31 rejections and nine historical targets. Twenty exact native/check/
  custom archives completed, including the [second batch](../results/cold-storage-batch-02/assessment.md). This made room for the pending cold comparisons;
  it is storage maintenance outside their timers, not a compilation speedup.

- Item 4.1 now has a std-only exec wrapper and shared Cargo routing rules in
  `b54dc6e` / `c341296c`. [Debug/release qualification](../results/lightweight-wrapper-release-01/assessment.md)
  passes 268 tests, fifteen actual process probes/dylib commands, five manifest
  checks, 99 original launcher checks and historical-tool execution. The VM is
  unchanged. Version-probe overhead falls from 10.53 to 1.75 ms; this is not
  project build-time evidence. The pgrust API qualification passes with identical
  artifacts, as does Nushell. [Fifteen pgrust cycles](../results/lightweight-wrapper-pgrust-repeated-01/assessment.md)
  reduce paired wall time 4.57% and CPU 4.46%; the first Nushell observation
  was slower. [Repeated Nushell edits](../results/lightweight-wrapper-nushell-repeated-01/assessment.md)
  now reduce paired wall time 4.24% and CPU 1.94%, with all ninety artifacts
  matching. Six balanced cold histories remain required. New manifests
  verify the third executable and preserve historical two-binary compatibility.
- Item 1.5 now includes [actual Cargo unit attribution](../results/interface-nushell-units-01/assessment.md)
  for a generic API edit: all modes rebuild 19 units. Native nu-command takes
  6.57s versus 1.12/1.24s custom checks in this instrumented sample. Distinct
  host/library/test nu-protocol configurations are required; crate-name-only
  merging is unjustified. Overlap and instrumentation remain explicit.

- Item 2.5 now has pinned generic-interface case specifications and a tracked
  `--case-file` harness with independent reconstruction of source states, test
  selection and mode order. [Pgrust qualification](../results/interface-pgrust-qualification-01/assessment.md)
  passes all four original tests and wrong-edit controls after generalizing the
  hash API; nine primary commands, three checks and six paired artifacts verify.
  [Nushell's constructor qualification](../results/interface-nushell-qualification-01/assessment.md)
  also passes its fourteen original tests and controls. These single pairs are
  separate from the repeated runs. [Fifteen pgrust cycles](../results/interface-pgrust-repeated-01/assessment.md)
  now verify 180 commands/90 artifacts; the experimental paired wall change is
  −1.14%, a small descriptive difference. [Fifteen Nushell cycles](../results/interface-nushell-repeated-01/assessment.md)
  also verify 180 commands/90 artifacts, with +1.12% paired wall change.
  Its original/wrong-edit artifacts change after cycle zero; corresponding
  engines always match and the generic-edit artifact is stable. This additional
  cache-history discrepancy remains unresolved. Neither interface result
  demonstrates a material gain from the experimental call path.
- A real disk-full failure exposed unsafe benchmark recovery. The original
  [partial held-out run](../results/resumable-bulk-heldout-failure-01/assessment.md)
  is preserved and its source restored. Atomic source/receipt publication,
  staged restoration and waited-for children pass ten failure-injection checks,
  including three real child processes. The fresh Nushell retry completed;
  [all seven held-out cases](../results/resumable-bulk-heldout-recovery-01/assessment.md)
  verify 588 commands, 105 pairs and 294 artifacts across the two histories.
  None exceeds 5% paired wall regression; both primary token gates stay failed.
  No unrelated process or cache was changed.

- The current resumable/bulk engine (`001065a` / `78e60cdd`) independently passes
  [47,004 mixed validation commands](../results/resumable-bulk-native-01/assessment.md),
  [245 TLS/destructor commands](../results/resumable-bulk-tls-01/assessment.md) and
  [fresh fre replay](../results/resumable-bulk-fre-01/assessment.md): 382 body passes,
  seven ignored and 382 fresh native executions. Explicit tool/mode selection,
  original assertion checks and a reusable bounded coordinator replace archived
  hardcoded drivers. Actual unwinding remains unsupported. Both primary token
  performance gates still fail narrowly; broader correctness does not waive them.

- The additional private-array reuse census (`f9bd49c`, isolated tool `71605527`)
  passes 15 exporter/observer tests and preserves both original exported artifacts
  and assertions on the exact `e89de7f8` VM. A typed join passes three tests and
  checks all function IDs/operations and exact counts in fresh profiles. Its
  [weighted result](../results/aggregate-reuse-weights-01/assessment.md) is only
  0.0000073% additional folded frame bytes and 0.1233% token. This narrow change
  is parked; broader layout proofs remain open. The next native-call step uses
  [resumable guest frames](../benchmarks/experiments/resumable-native-calls/PLAN.md)
  to avoid excluding whole functions for loops or cold unsupported operations.

- Items 3.2 and 5.4 now have a bounded full-CFG liveness analysis and shared
  read-before-write visitor (`b252588`), plus persistent full-u128 register pairs
  across native branches/calls (`d664bce` / `e89de7f8`). Debug and release pass
  240 workspace tests, including VM continuations, alias/cache interactions,
  exact budgets and x19–x28/SP/LR through nested calls and faults. Ten CLI checks
  pass and the receipt verifier rejects falsely claimed runtime flags. The
  [experiment plan](../benchmarks/experiments/bounded-native-calls/VALUE-LIFETIMES-NEXT.md)
  retains the original b2 performance gates. The completed
  [168-command E2E result](../results/persistent-e2e-01/assessment.md) improves
  token 23.6% paired and folded 4.2%; token passes its target, folded misses 10%.
  Fresh profiles now guide an additional private-frame-reuse census. The new
  runtime remains experimental and lacks held-out/broader qualification.

- `93abea7`: repeated source-edit cycles, CPU accounting, portable verifier and
  typed artifact diagnostic. All 63 commands completed. [Assessment and preserved
  identity failure](../results/paired-repeated-token-01/assessment.md).
- `a2a0e04`: typed encoding-limit declines, relocation validation, explicit JIT
  safety/thread contract, and five new tests. [202 passing workspace tests](../results/review-codegen-limits-01/summary.json).
  Boundary tests do not claim that the current region cap naturally overflows.
- Added the toolchain pin, concise README, generated status/results index,
  mechanism-only architecture, changelog and historical snapshots. Fixed the
  stale no-Git continuation rule without deleting old evidence or quarantine.
- Added a [Git-backed build index](../benchmarks/tool-builds.json): commits
  `32f5e2f`, `6b2c61f` and `a2a0e04` reconstruct source keys `6bf10fda`,
  `57a54edd` and `b2aa6efe`, with installed binary hashes verified. The legacy
  source-key algorithm omits compiler identity; the index records the compiler
  and target separately rather than claiming a stronger cache key.

- Implemented explicit native profile/jobs/test concurrency/compiler flags and
  an independent library-test Cargo-check reference. Two pgrust qualifications
  completed 168 commands in total, including 42 check commands. Native flags
  were also confirmed in Cargo's selected test-target fingerprints. Exporter
  pass timing scopes are separate and nested times are not added together.
- Added a tracked nine-workflow configuration, serial corpus runner, reusable
  detached supervisor and verification for paired and interpreter/JIT runs.
  The benchmark rejects Python `-O` rather than silently dropping its assertions.

- The [full repeated corpus](../results/native-controls-corpus-01/assessment.md)
  completed all 756 commands across nine workflows, including 189 independent
  checks. Source pins/restoration and 378 custom artifacts were verified. The
  three fre workflows retain unresolved cross-history layout differences.
- Two typed native-call censuses passed eight and nine diagnostic tests and
  matched the prior profile/call totals. The expanded scope supports selecting
  a bounded call-tree experiment with explicit terminal traps and whole-tree
  readiness/budget guards. This is an opportunity result, not an implemented
  runtime gain. The corpus receipt now clears stale child-exit fields between
  cases; that fix was made after the measured scripts were released.

- Implemented the custom bounded native Call/Return path and its explicit
  launcher/benchmark option. All 225 workspace tests pass in debug and release.
  The [three-cycle E2E result](../results/bounded-native-e2e-01/assessment.md) covers
  168 commands/84 artifacts: token improves 14.4% paired but folded regresses 3.0%.
  Both predeclared gates fail; the version stays experimental. This addresses
  the native-call direction without claiming readiness or resetting success criteria.

The [ordinary-region Call integration](../benchmarks/experiments/bounded-native-calls/REGION-CALLS-NEXT.md)
is implemented in `26833c3` / `2f31c6a0`, with 231 workspace tests passing in
debug/release. Its [three-cycle E2E result](../results/native-region-e2e-01/assessment.md)
improves token 19.3% paired but regresses folded 1.4%, missing both original gates.
The options remain experimental. Fresh profiles and same-process emitted-code
attribution are complete. The diagnostic tool passes 233 debug/release tests.
[Register liveness/persistence](../benchmarks/experiments/bounded-native-calls/VALUE-LIFETIMES-NEXT.md)
is now implemented and measured above. The
[next diagnostic](../benchmarks/experiments/aggregate-reuse-census/PLAN.md)
has completed and parked private primitive-array reuse. Existing argument-zeroing
and unused-local censuses also remain parked; resumable native Calls are next.
The remaining accepted design work above is prioritized follow-up, not a claim
that a production Rust development engine is complete.

- Item 3.1 now has initialized VM/TLS guest-frame backing (`fca1e96`) and a
  checked descendant-continuation boundary (`1264921`). All 249 workspace tests
  pass in [debug](../results/resumable-boundary-01/summary.json) and
  [release](../results/resumable-boundary-release-01/summary.json), one ignored.
  The nine new tests qualify storage/publication invariants. Resumable native
  emission, VM integration and the original E2E gates remain outstanding.

- Item 3.1 now has a working resumable Call/Return emitter and VM specialization
  (`5574d10`, integration `e1bec3e`, tool `035ef708`). All 256 debug/release tests
  pass, including recursion through 1024 frames, exact descendant fallback,
  host ABI, limits, warm alias copies and TLS. Twelve CLI checks and
  [both original artifacts](../results/resumable-real-smoke-01/assessment.md)
  pass. The [completed original E2E comparison](../results/resumable-e2e-01/assessment.md)
  improves folded 10.6% and token 15.0%, with CPU improving. Only folded passes;
  the combined gate fails. Fresh exact-code profiles will guide the next change.
  These results do not qualify the runtime for large-project adoption.

- Fresh exact-code profiles of resumable Calls found 56.3% folded and 17.4%
  token samples in required clearing. One bounded 64-byte initialization change
  (`001065a` / `78e60cdd`) preserves every byte and passes 257 debug/release tests.
  Its [E2E result](../results/resumable-bulk-e2e-01/assessment.md) improves folded
  19.51% and token 19.95%; token narrowly misses its 20% gate. One fixed-tool
  replication is planned before further runtime tuning. The failed gate stays
  recorded; current performance/coverage still does not qualify large-project use.
- The full native validator now has a tracked immutable-tool/mode driver with
  unchanged assertion checks and verified VM command flags. Helper qualification
  passes; full new-mode execution, separate TLS and fre coverage are pending.

- The one predeclared fixed-tool replication also narrowly misses token's 20%
  gate: 19.97% token and 19.15% folded, with CPU improving. Both failed combined
  decisions remain in the [two-run report](../results/resumable-bulk-replication-01/assessment.md).
  Stop repeated attempts/batch tuning and characterize broader compatibility.
  Explicit-mode native, TLS and fre drivers are ready; helper checks preserve
  the full TLS case matrix. This does not waive the original gates or retain
  the experimental mode.

- Item 9.2 now has bounded, separately prepared object-only reclamation with
  exact completed-workflow/corpus provenance, lock and open-file checks, an
  immutable per-file inventory and preservation verification. Six completed
  public Nushell native targets were reclaimed. Hard-linked path totals are
  explicitly distinguished from unique inode sizes and observed free space.
  Private caches, bytecode snapshots, reports and all non-object files remain.

- Item 9.2 also has a qualified object-only path for completed host workspace
  checks, verifying archived sources/logs/test counts and installed copies.
  Thirty-one rejection cases, hardlink preservation, three real host
  qualifications and two historical workflow checks pass. The first host
  inventory contains only 0.351 GiB of unique object inodes; object cleanup
  alone is unlikely to fund all six fresh large-project cold histories.
