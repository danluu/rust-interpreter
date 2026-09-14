# Review of the September 13 12:45 suggestions

Read the replacement user-owned `suggestions.txt`, SHA256
`4d74b3dc8b79ad7655a153c8aaf7485677e4bbe677b5a7bc7bec683a3da80c2f`.
It remains unmodified and untracked. This review supersedes the previous file's
next-work priorities without changing completed measurements or ownership.
Re-read after the renewed user request during the13:09–13:15 work interval;
the file still has this exact hash and contains no later replacement.

Several recommendations are already implemented. The guarded SipHash ranges
are adopted, ordinary native regions already precharge their static instruction
count once per region, and successor-only flushing has completed its full
comparison. It fails the required wall gate: observed improvement 3.25%, A/A
7.32%. The four remaining projects stay unstarted. A passing screen did not
establish adoption.

The other Rust session owns the compiler/Cargo investigation. Preserve those
worktrees and processes; recommendations here do not authorize taking them over,
starting concurrent heavy work, or increasing this host's two-worker setting.

| Items | Decision and evidence limits |
| --- | --- |
| 0 Cost table | Use the pinned measurements to prioritize, preserving their scopes. A historical 3.0s test cannot be a lower bound on the newer 2.65s VM stage. Independent stage medians and ratios are not additive. The parser's exporter cost is actionable, but a comparison with native does not establish that removing the reuse cache would help. |
| 1.1 Host critical path | Treat the profiled host build as a useful target, subject to its actual dependency timeline. Host-library O1 already targets that stage; it is incorrect to say all seven candidates ignored it. A profiled unit's wall duration is not automatically its contribution to an unprofiled command. |
| 1.2 Host debuginfo | A reasonable separate, explicit compiler-policy candidate for the compiler session. Current `host_proc_macro::library_additions` preserves debuginfo. First inspect the exact unit's existing flags; a policy cannot save work already disabled. Bind routing/options/cache identity, retain checks and original build-script results, and document the debugging/backtrace tradeoff. Do not promise 20–35% or silently change defaults. |
| 1.3, 1.6 Throughput | Preserve as a prospective matched native/custom configuration. Eight workers/threads are not admitted by available core count or these suggestions. Keep two workers here. Frontend threads do not prove parallel expansion or ideal scaling; the pinned compiler's behavior and full exporter correctness still need qualification. |
| 1.4a Workload split | Do not change pinned benchmark workloads to manufacture an engine gain. A smaller build-script dependency can be documented as an application design option; removing one unit does not prove its entire duration disappears from the critical path. |
| 1.4b rlib reuse | Reject SVH-independent rmeta equality as a sufficient reuse proof. Metadata need not encode every native body and codegen dependency: changing a non-generic function's implementation can change a build script while preserving its public interface. Require complete compiler-proven body/configuration/dependency validity before reusing code. Fresh checking alone does not validate an old rlib. |
| 1.5 Host Cranelift | Defer to the compiler session's owned investigation. Verify the precise pinned failure/fix and host ABI before proposing a test. No Cranelift/LLVM guest backend or foreign-purpose guest interpreter is introduced. The suggested speedup is unmeasured here. |
| 1.7, 4.1, 4.2 Cargo info cache | A prospective small-project primary is reasonable where the mechanism applies. Measure that project's actual probes/prefix; Nushell's 0.17s is not established for rg-aot or pgrust. Declare selection and gates before timing and retain regression guards; one favorable private-project screen cannot alone establish general adoption. Avoid duplicating the compiler session's patch. |
| 2.1 Flush | Finished: retain the passing screen and failed full primary. All 154 full commands preserve assertions and restoration. Park unchanged standalone timing; keep correctness evidence for a justified later composition. |
| 2.2 Memory guards | The 265M disjoint-frame census already led to adopted guarded ranges and local facts. Do not implement or time it again. The current work is a disabled test-only partition of the adopted emitter, separating checking from data transfer using existing captures. It is not another generic address-check runtime variation. |
| 2.3 Budget | Already once per region: `jit.rs` emits static count, comparison, insufficient-budget branch and subtraction before the body. Existing tails handle exact limits. Current saved budget samples are 106/1,651 and 99/1,439, about 6.4%/6.9%, not 11% on block. The narrower subtract-immediate/borrow-branch fusion was also already qualified and screened in `scalar-copy-budget`: it restores the debit on fallback, removes one net word per region, and failed its40-command primary (wall ratio1.023906, A/A8.80%). Do not recreate or retime that unchanged mechanism. Neither result supports the suggested per-op-to-per-region change. |
| 2.4 Protocol composition | Keep compatible composition as an option. The wider-clear/copy bundle failed its screen and remains parked. Publication/addressing/dispatch changes need concrete diffs and complete frame, fault and budget proofs. Do not infer additive gains from overlapping sample categories or combine with an already-existing budget mechanism. |
| 2.5 Token floor | Guest execution remains the largest current stage. Avoid an absolute claim that only guest work can cross a chosen native ratio: exporter/Cargo savings also reduce the complete command. Preserve the original unsplit test and its assertions. |
| 3.1, 3.4 Parser costs | Prioritize a parser-specific reuse/pass breakdown in the compiler workstream, reusing saved receipts first. The token result of 172 unsupported recipes and 22.88ms does not establish the parser's count. Reconcile counts with its own lowered/reused graph before changing recipe coverage. |
| 3.2 Incremental graph passes | Conditional on measured pass cost and complete keys. Template hash plus callee set is not sufficient by itself: options, transitive transformations, graph discovery/order, layouts, constants and allocation/relocation identities can affect output. Preserve full strict checking and exact original artifacts/outcomes. The proposed 0.15s/0.35s targets remain hypotheses. |
| 3.3 Artifact digest | Keep the prior audit prerequisite. Executed bytes must remain bound to the catalog and integrity checks. Do not land a digest shortcut solely from graph size or an assumed 0.1s cost. A qualified change can join an appropriate future exporter candidate. |
| 3.5 Oversized functions | Keep 16 MiB as the default; the 32 MiB screen did not pass. Region-demand compilation remains a larger design option, not a required next step from reachability alone. Compare its expected benefit and complexity with measured parser lowering work before implementing it. |
| 4.3 Cargo memoization | Agree: do not bypass resolve/fingerprint correctness for an assumed fixed startup cost. |
| 5.1 Noisy measurements | Distinguish failure to meet an engineering gate from evidence of zero benefit. Preserve completed raw results and gate values. Do not introduce a retrospective 8% threshold or rerun until a quieter outcome appears. A future protocol may predeclare a bounded high-variance classification/retry rule, with every attempt retained and no relaxed adoption gates. This full flush result is below the proposed 8% threshold anyway. Declare frontend primaries from mechanism scope before observing their outcome. |
| 5.2 Disk | Already applied: Nushell is last and unstarted after primary failure. Keep its recorded reservation and per-command floor. Retire only exact completed owned caches after receipt/open-file checks; preserve snapshots and other sessions. The latest cleanup preserved 7,186 protected files and recovered about 5.4 GiB of free space. |
| 5.3 Lock utilization | Accept small read-only reviews of saved evidence while waiting. Builds, profiles, correctness fixtures and substantial offline analyses still consume CPU/memory/I/O and retain serialized admission. Calling a task offline does not make it harmless to a running timing study. |
| 6.1 Own-build hygiene | Deferred to a real packaging change. The diagnostic controller already uses explicit two-worker builds and bounded debug settings; no workspace-wide profile change or feature churn in this experiment. |
| 6.2 Setup accounting | Record setup/build durations by exact tool key. Current full comparisons reuse installed, qualified tools; they do not rebuild the toolchain per case. Keep setup cost separate from edited command measurements. Existing terminal receipts retain elapsed time; improve reporting when touching setup, without repeating completed builds. |
| 7 Stop list | Follow the corrected dispositions above: no duplicate guard/budget implementation, no premature parser capacity change, no inference of zero effect from noisy failures, and no frontend work outside this session's ownership. |
| 8 Order | Finish the already-qualified memory partition, choose the next runtime component from its actual cost breakdown, and preserve all completed failures. The host-debug/Cargo-info/parser-pass suggestions are useful compiler-workstream candidates under their stated proof and admission conditions. They do not preempt a running command or authorize eight-worker experiments. |

Evidence: [adopted runtime and compiler](../results/guarded-local-facts-main-final-audit-01/assessment.md),
[flush full result](../results/successor-only-flush-full-01/assessment.md),
[current sample attribution](../results/adopted-runtime-sampling-01/assessment.md),
[native protocol parts](../results/native-protocol-census-01/assessment.md),
[token reuse reasons](../results/reuse-misses-analysis-01/assessment.md),
[parser comparison](../results/pgrust-parser-edits-incremental-history-01/assessment.md),
[compiler workstream](../benchmarks/experiments/strict-warm-build/PROGRESS.md),
[memory diagnostic plan](../benchmarks/experiments/memory-operation-parts/PLAN.md).

Budget-specific cross-check: [prior fusion plan](../benchmarks/experiments/scalar-copy-budget/PLAN.md),
[qualified failed screen](../results/scalar-copy-budget-screen-token-01/assessment.md).

Follow-up through14:46: the renewed read has the same suggestions hash. The
memory-pair census found only30/13 affected saved samples and remains deferred;
the counter/flush composition failed its40-command wall and CPU gates. Neither
is retimed. The exact indirect-call diagnostic now supports a general native
transition:1,025,947/843,776 validated calls, only20/23 unprepared callee entries,
and all caller continuations ready. Proceed with complete signature/layout
metadata and ordinary VM fallback, then measure real changed-source commands.
The explicit observer feature uses a main-thread executable; its rejected
libtest replay and all earlier failures remain closed evidence. Setup durations
are now recorded by tool for the counter experiment. Compiler/Cargo suggestions
remain with the other workstream; no ownership or worker-count changes follow.

Follow-up through 15:22: reread the requested file; its hash is still unchanged.
The standalone indirect screen and its successor-flush composition both failed
their wall gates. The latter observes 3.15% improvement versus 9.17% A/A. Keep
the high variance visible; do not infer zero effect, retrofit the proposed 8%
retry threshold, or start the larger comparisons. Its exact profiles preserve
logical/backend counts and remove only proved dead spill words. Next join the
existing typed direct-call targets to saved protocol samples and adopted profiles
to choose a mechanism from actual remaining costs. No compiler-workstream or
worker-count change follows from this review.

Follow-up through 15:49: the requested file still has the same hash. The call-cost
join led to bounded CFG and constant-memory initialization diagnostics. The
extension passes ten controls per profile but covers only 16 / 20 clearing
samples (0.97% / 1.39% of generated-code samples, before guard/padding costs).
Defer runtime clear elision; large eligible call counts do not establish savings.
This closes the diagnostic without repeating any timing or changing the adopted
runtime. Continue reviewing broader remaining costs within runtime ownership.

Follow-up through 16:34: the requested file still has the same hash. Bounded-tree
coverage justified a new resumable bridge, retaining full type/borrow checking,
ordinary admission fallback and checked fault publication. The experiment now
passes 556 workspace controls per profile; strict/cache and real-workload
qualification remain pending. A global quarter-arena code quota limits duplicate
trees, and guarded-body exclusions propagate to ancestors. No timing result or
adoption claim follows. The six focused runs, including all three early compile
failures, are archived with 1,202 source bindings and 222 exact source blobs.

The bounded-tree runtime prototype is parked after its 40-command primary: wall
ratio 0.995499 versus 9.9249% A/A, CPU ratio 1.021747. All 556 workspace controls
per profile, 119 strict commands and three exact original profiles pass. The
closure verifies 1,958 inputs, 56 artifacts and 380 source bindings. Full,
held-out and repeated runs remain unstarted. Review repeated cursor/budget
adaptation before another materially changed candidate. [Bridge result](TREE-BRIDGE-20260913.md).

The shared-cursor bridge also fails its 40-command primary wall gate: 1.70%
improvement versus 4.1545% A/A, with CPU improving 0.10%. All assertions and
restoration pass. Its closure verifies 1,958 inputs, 56 artifacts and 380 Git
bindings. Full/held-out/repeated runs remain unstarted. Inspect actual native
costs before another candidate. [Result](TREE-SHARED-CURSOR-20260913.md).

Follow-up through 18:03: the suggestions file remains unchanged. Exact saved
native samples motivated hoisting the heap-address bias, distinct from the
parked selector/CCMP variants. Its qualified 40-command primary passes narrowly:
wall improvement 2.88% versus 2.747% A/A, CPU improvement 0.59%. Proceed to the
original full gates; no runtime adoption follows from the screen. Keep the
compiler/Cargo suggestions with their existing workstream and two-worker
resource limits. The per-region budget work and SipHash guards are already
implemented; neither is a new opportunity. Transparent compression of closed
diagnostic JSON reclaimed about 1 GiB with every original SHA unchanged.
[Qualification and limitations](HEAP-ADDRESS-BIAS-20260913.md).

Follow-up through 18:14: the heap-address bias fails its full token gate after
154 commands: 1.02% wall improvement versus 3.8043% A/A, and 0.15% CPU regression.
Correctness, original assertions and restoration pass. Park it and cancel the
four unstarted project cases; the passing 40-command screen does not override
the full result. Review saved immediate-materialization sequences next, with
no guest rerun or performance claim from static code size.

The immediate-materialization census is also deferred: removable low-zero seeds
cover only 8/1,966 and 0/1,560 generated sample PCs. Large static word savings
are mostly cold. Before a larger call-frame change, join the already-qualified
confined-memory proof to saved call costs. The old V6 scalar ABI is implemented
and parked: its real screen saved about 170 ms execution while adding about
144 ms Cargo work. Do not repeat it unchanged. Any new runtime-only scalar
lowering must establish a separate safety contract and measure its preparation
cost inside complete edited-source commands.
