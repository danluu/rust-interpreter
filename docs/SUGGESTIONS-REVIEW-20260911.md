# September 11 review decisions

This supersedes the September 10 disposition for the replacement suggestions
file (SHA256 `a72054eca205a5fc8ed083157e8357a6a39b216ca73fcb8c4e5dc3b595bea3a7`).
The original file is user-owned and unchanged. The review identifies a real
process failure: too much work on small candidates and preservation machinery,
too little on complete-command latency and usable project workflows.

The scalar compiler/runtime is now ordinary `crates/` source on branch
`experiment/scalar-value-abi`, commit `840fdb5`. It exactly matches the qualified
`aa56492e` source. The timing tool `ba4ad407` combines that compiler/runtime with
the retained `9637b0ac` wrapper. Its Cargo route passed all 19 publication checks.
The original tests pass on both fre workloads. These are correctness results.

A [short screen](../benchmarks/experiments/scalar-value-workflow/SMOKE.md)
now precedes the previously planned full histories. It requires at least 8%
token complete-command improvement, improving CPU and separate 5% folded guards.
Five real edits per workload are measured; cold and wrong-edit controls remain.
The screen is now complete: token −0.74% wall/−2.66% CPU, folded −0.41% wall/+1.07% CPU.
It failed its target, so the candidate is parked and the full histories are stopped.
[Decision](../results/scalar-edit-smoke-01/assessment.md). The source-branch maintenance
changes pass 334 release Rust tests, 11 Python tests and formatting;
[qualification](../results/review-maintenance-01/assessment.md).

“Accepted” below specifies direction, not a claim of implementation. Work
marked next follows the timing result; unrelated changes do not enter that
fixed comparison. Historical failures are not relabelled as passes.

| Item | Decision and action |
| --- | --- |
| 0 Verdict | Agree on prioritization and weak adoption evidence. Correct one arithmetic claim: 1.48s frontend/export is below a 1.97s complete native command; zero guest execution could beat that control. It leaves only about 0.49s for guest execution and other overhead. Separate-run subtraction is not causal attribution. |
| 1.1 Detectable effect | Implemented the 8% short screen before full primary/held-out work. It uses twice the largest recent token A/A envelope as a screening heuristic, not a confidence bound. Park failures without repeated attempts. |
| 1.2 Scalar number | Done and parked: token improved 0.74%, below the 8% screen. No full comparison follows. |
| 1.3 Register allocation | Accept as a structural candidate after profiling the scalar result. Design liveness across calls/back-edges, spills, u128 pairs and host ABI together; x19–x28 are not ten freely available guest registers. |
| 1.4 Export overhead | Measured on seven byte-identical token exports: graph lowering 691ms, hash 49ms, publication 30ms, serialization 14ms, validation 5ms. Small publication wins cannot fund a full primary. Graph reuse remains substantial; see the export-cost result. |
| 1.5 Hybrid analysis | Accept explicit cost modelling. Native compilation is paid per Cargo target; per-test guest timings alone cannot predict mixed execution. Report lower/upper bounds when native test timings are absent. No hidden native fallback. |
| 1.6 Unfiltered suite | Accept and schedule one fre-kernels suite attempt after the latency controls. Report native all-tests time, guest executed/ignored/unsupported lists and setup costs separately. Direct body runs cannot be presented as successful libtest execution. |
| 2.1 Control defaults | Correct the prose now. Done on the source branch: both runners share explicit O0/incremental, 18 jobs/default threads. Preserve fixed existing scalar settings (four custom jobs) during this comparison. |
| 2.2 Native stage split | Existing 135 edited native commands now have rounded suite timing and non-suite residuals; Nushell type-relations uses a grouped harness. The new calibration preserves actual Cargo timing and separately records diagnostic binary repeats. Repeats are not the original execution time. |
| 2.3 Check floor | Accept a per-row check reference and exporter overhead. Correct the claim that these rows execute nothing useful: they do run selected original assertions, but their savings predominantly avoid native code generation/linking. |
| 2.4 Workers | Agree that interactive wall latency should choose a development preset. The source branch now defaults both runners to 18 custom workers; report CPU cost and qualify fresh matched controls before performance claims. Preserve the historical CPU-gated failure and do not change workers inside the scalar comparison. Shared-host contention remains a reason to expose a worker limit. |
| 2.5 Tuned native | Now first: effective profiles inspected for all five projects (15 queries); pgrust/Ruff already use line tables, all five use unpacked split info. Fre calibration is inconclusive: line tables saved 7.86%, below its fixed 8% screen; debug=0 saved 5.17%. No preset was selected. Check a large target separately and run the unfiltered suite. No fastest-native claim. |
| 2.6 Cold | Accept a cold column alongside warm edits, with empty per-mode caches distinguished from OS/download/tool bootstrap coldness. Recompute from receipts; do not mix worker presets. |
| 2.7 Fixed anchor | Accept. Before another integration, compare with the best previously retained engine for each primary in the same session. The immediate predecessor and a repeated 5% allowance are insufficient protection against cumulative regressions. |
| 2.8 Drift | Accept. Use paired ratios for changes and same-history native ratios; absolute medians from different sessions are historical observations, not cross-version speedup estimates. |
| 2.9 Determinism | Accept diagnosis before function reuse: compare the existing allocation traces across identical-source cache histories. Stable semantic identities/relocations are required even if serialization becomes deterministic. |
| 3.1 Runtime modes | Accept consolidation around resumable calls plus persistent registers, with the interpreter reference retained. Audit users/options before removing trees/stubs; do not delete modes in the measured scalar candidate. |
| 3.2 Call ABI | Scalar result registers and mixed return bridges are already implemented, including native continuation calls. Remaining frame/initialization work must follow profiles; descriptor laziness needs observable-state and fault proofs. |
| 3.3 Resume preparation | Accept prepare-once as a candidate only after counting actual reentries and verifying memory/register growth invalidation. Immediate native reentry must make progress at unsupported instructions and preserve budget/profile ordering. |
| 3.4 Cached JIT | Accept per-program compiled-code reuse with fresh guest state and explicit thread ownership. First measure repeated short executions; never reuse guest heap, TLS, profiles or stack accidentally. |
| 3.5 Memory model | Accept a design comparing current tagged arenas, provenance-aware fast paths and reserved virtual address space. Include readonly bounds, reallocating heaps, pointer arithmetic and unsupported platforms. Removing checks without an invariant is not a design. |
| 3.6 Budget register | Do not restart the parked x22 experiment. Its measured effect was below the screen. Reconsider only with structural region formation/allocator changes while preserving exact terminal budget behavior. |
| 3.7 Copy/zero emitters | Accept consolidation when removing old call modes. Keep overlap-safe memmove and exact initialization semantics; performance-sensitive instruction sequences need equivalence checks. |
| 4.1 Wrapper status | Correct the documentation: the exec wrapper is present in the retained tool and selected by the launcher. Its standalone cold experiment failed its declared gate; this does not make the deployed wrapper absent. Future gates follow bounded mechanism and latency objectives. |
| 4.2 Pipeline reuse | Accept eliminating redundant publication/hash/proxy work after stage attribution. Dependency cache sharing must distinguish wrapper/rustc flags and MIR encoding; changing a tool key must not reuse incompatible metadata. Measure multi-entry export separately from selected-entry export. |
| 4.3 Observer costs | Accept named stage costs and opt-in diagnostic output. The byte-write proof supports a retained optimization, so disabling diagnostics must not disable its correctness analysis. |
| 4.4 MIR encoding | Investigate the reachable dependency set. Most selected crates may need all transitive MIR, and std MIR does not provide third-party MIR. Measure metadata size/build cost before narrowing flags. |
| 4.5 Function reuse | Accept reevaluating on token, not extrapolating Nushell's 71ms. Diagnose determinism and define semantic dependency keys first. |
| 5.1 Source in Git | Done: exact qualified source committed under `crates/` in `840fdb5`, in a small separate worktree. Existing patch recipes remain historical reproduction evidence; future source development uses normal diffs. |
| 5.2 Formatting | Done in dedicated commit `5493fd6`. The normal check entry point enforces formatting; the full release suite passes. Formatting is not a performance change. |
| 5.3 Relocation structure | Accept correcting stale mutation comments, replacing tuple metadata with named structs and declining bounded/unrecognized cases. Keep impossible internal corruption distinct from supported optimization declines; do not silently swallow all failures. |
| 5.4 Encodings | Accept named offsets and encoding helpers when touching those paths; remove obsolete call modes before polishing code scheduled for deletion. |
| 5.5 Traversal/errors | Accept shared successors/terminal/memory-effect APIs and structured lowering errors incrementally. Register visitation alone does not define alias, call or CFG semantics. |
| 5.6 Unsafe contract | Confirmed malformed sentence and debug-only readiness checks. Done on the source branch, with the full release suite passing. |
| 5.7 Python | The workspace check now runs all 11 existing Python tests successfully. Accept a shared package for new code. Preserve historical evidence scripts required by retained receipts; do not delete them merely to lower a file count. Stop adding independent archival subsystems. |
| 5.8 Legacy workspace | Done on the source branch: default-members are the custom bytecode/exporter crates, verified with Cargo metadata; `--workspace` still checks all members. Audit callers before removing legacy modules/options; no guest execution is delegated to Cranelift. |
| 6.1 Existing invariants | Agree. Preserve atomic JIT declines, hard relocation errors, budget/fault ordering and same-thread code ownership. |
| 6.2 Tree register preservation | Covered by current ABI probes but difficult to maintain. Prefer removing obsolete trees/stubs after auditing usage; until then preserve their calling convention tests. |
| 6.3 Terminal faults | Documented next to `Boundary::finish` on the source branch: partial Call state is terminal and cannot be resumed. Future recoverable faults require a separate commit/rollback contract. |
| 6.4 Mode combinations | Accept adding the two missing combinations if those modes survive the audit; otherwise remove the supported surface and its claims together. |
| 6.5 Random differential | Accept a deterministic valid-program generator with persisted seed/program on failure, spanning loops, calls, width truncation, aliasing and budgets. Existing table-driven scalar tests are not random CFG coverage. |
| 7.1 Current identities | Fix RUNTIME-NEXT and add missing integration/parked/scalar entries to CHANGELOG. Link the authoritative current status instead of repeating stale hashes in several headers. |
| 7.2 STATUS length | Implemented a concise manifest-driven current table, coverage/limits and next action; link experiments for detail. Historical detail is already in Git/results and need not be copied into more snapshots. |
| 7.3 Claims/prose | Accept concise scoped headlines. Do not claim fastest-native performance, whole-suite coverage or universal frontend wins. Include check-floor and cold data rather than repeating generic caveats. |
| 7.4 Identity naming | Use `git7/tool8` for ordinary builds. Explicitly label `ba4ad407` a composition of compiler/runtime and a separately built wrapper; inventing a single source-key interpretation would hide that distinction. |
| 7.5 Experiment directories | Accept one directory per new experiment, revisions in Git. New smoke code is in the existing scalar workflow directory. Preserve old versioned recipes referenced by evidence. |
| 7.6 History copies | Stop creating more file copies; use tags/commits. Preserve linked old snapshots until their inbound references are migrated. |
| 8.1 Commits | Agree on outcome-focused implementation/decision commits and batching routine receipt updates. A rigid three-commit cap is less useful than reviewable code and an explicit decision. |
| 8.2 Branches | Actual scalar source now has its own branch/worktree. Retention can integrate a reviewed source change; parked candidates remain accessible in Git. Do not rewrite shared historical evidence commits. |
| 8.3 Results retention | Accept compact committed summaries and decisions for new work, local detailed inventories/raw data and stable content hashes. Preserve existing evidence paths. Document this policy instead of proliferating archival receipts. |
| 8.4 Cache deletion | Accept deletion of exact owned completed disposable caches after terminal/ownership/open-file checks and preservation of sources, artifacts and evidence. Index absence is not proof of disposability; the index is incomplete. A seven-day TTL currently frees none of the two-day-old experiments. Private caches remain outside this cleanup scope. |
| 8.5 Storage time | Agree. Finish the already running verified batch and stop additional archival before the scalar screen. Storage maintenance is not engine progress. |
| 8.6 Index | Accept a manifest-driven index with date, source/tool, case, delta, decision and successor. Avoid inferring retention from commit verbs or result directory names. |
| 9 Suggested order | Adopt scalar timing first, then tuned native/export costs and a usable suite workflow. Cheap documentation/source/check fixes can accompany that work. Do not change workers or binaries in the middle of the scalar comparison or reverse old gates after seeing data. |

September 12 priority update: the supplied file still has the same SHA256. [Export costs](../results/export-costs-token-02/assessment.md) and [native stages](../results/native-existing-stages-01/assessment.md) are measured. Next is [native calibration](../benchmarks/experiments/tuned-native/PLAN.md), followed by a usable unfiltered suite and structural runtime/export reuse work.
