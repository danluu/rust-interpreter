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

Follow-up through 18:47: reread the same suggestions hash after restoration.
The typed confined-leaf study now has a qualified runtime-only scalar reference
IR. All 483 resolved functions are acyclic within its bounds; the hot selection
retains 11.23M / 16.30M native calls. The five new reference controls pass alongside
the 13 access controls in debug/release. Preserve V5 and avoid the parked V6
exporter cost. Next qualify direct AArch64 emission and the unchanged-on-failure
Call boundary, then use the original primary/full edit workflows. Node counts
are not a native-time model. No new compiler ownership or worker setting follows.
[Scalar evidence](../results/confined-scalar-ir-coverage-01/assessment.md).

Follow-up through21:24: the suggestions hash remains unchanged. A custom scalar
leaf body and native Call transaction pass590 workspace controls/profile,121
strict/cache commands and six exact original profiles, but their40-command
primary fails (wall1.003720, CPU0.996103, A/A wall3.0585%). Four native registers
for block-local scalar values then pass593 controls/profile and the same real
qualification. Their primary observes4.00% wall /1.53% CPU improvement inside
7.6260% wall control variation and fails its existing gate. Keep both results,
cancel larger comparisons, and do not retime unchanged candidates. The scalar
bridge already uses ordinary effective capacity bounds; the concrete remaining
difference is its missing guarded caller-frame argument-address path. Review
that path and preserve private failure replay. This is runtime work only;
compiler/Cargo ownership, two-worker limits and strict frontend checking remain.

Follow-up through 22:15: the suggestions hash remains unchanged. Guarded caller-
frame argument addressing and removal of a redundant private scalar-entry budget
check pass 594 workspace controls per profile, 121 strict/cache commands and six
exact original profiles. The 40-command primary observes 1.38% wall and 2.04% CPU
improvement, inside 3.3145% wall A/A variation; its unchanged gate fails. Park this
revision and cancel larger comparisons. All assertion outcomes, source restoration
and candidate/control bytecode identities pass. Its 2,530 protected evidence
hashes remain unchanged after retiring disposable compiler intermediates.
[Screen and limitations](../results/scalar-call-guards-screen-token-01/ASSESSMENT.md).

Continue with a bounded saved-artifact census of constant expressions and unused
high halves in the scalar emitter. Reconstruct qualified emitted bodies first;
static words and successful scalar PC counts do not establish hardware time or
an end-to-end speedup. No new runtime candidate follows until that census identifies
material work. Keep the adopted VM as the control, full checking, two Cargo workers,
and the existing build/disk gates. Compiler/Cargo ownership remains separate.

Follow-up through 22:39: the suggestions file is unchanged. The saved scalar-body
census identifies 733–822 million dead pure-register word executions on successful
Calls in the original token block test. Most occur in copy_nonoverlapping's
precondition and define an unused high half. Nine observer controls and all saved
bodies pass after explicitly proving unconditional Trap branches; earlier failed
census attempts remain archived. This is a bounded static/path estimate, not a
hardware or timing result. [Census](../results/scalar-word-census-03/ASSESSMENT.md).

A custom bounded dead-register pass now matches independently compacted words for
all 137 saved bodies in debug/release. A std-only live probe adds 35,072 synthetic
native body attempts per profile, comparing complete private outputs even on
failure and preserved host registers/SP. Original memory operations, branches,
budget/profile updates and Call transactions are retained. Full VM qualification
and real edited-source timing are pending the unchanged workspace disk gate.
The small isolated probes do not use Cargo or the shared target and do not count
as end-to-end comparisons. Keep the adopted VM as control; no runtime adoption.
[Live probe](../results/scalar-dead-registers-native-probe-01/summary.json).

Follow-up through 23:12: bounded dead-register elimination passes 20 focused and
596 workspace tests/profile, 121 strict Cargo/cache commands and six exact
original profiles. Its primary has a 0.949959 wall ratio and 0.956743 CPU ratio,
but the 0.060657 A/A wall envelope makes the margin 1.010617: park it without
starting larger comparisons or changing the gate. The descriptive Cargo stage
is 161.7 ms lower despite a runtime-only revision; do not attribute that
variation to scalar emission. Scalar native bodies shrink 14.5% in token block,
11.5% in exhaustive token and 9.4% in folded prefilter. Next quantify constant
computations and duplicated arithmetic-result/overflow calculations in saved
real scalar bodies before picking the next revision.
[Primary assessment](../results/scalar-dead-registers-screen-token-01/ASSESSMENT.md).

Follow-up through 23:43: the width-alias candidate passes 600 workspace tests in
each profile, 22 native/Call controls, 121 strict commands and six exact profiles,
but its primary fails (wall 1.028289, CPU 0.987340; A/A wall 0.040899). Park it.
The preceding no-constant census prevented an unnecessary constant folder;
117 million modeled pack/cast aliases still did not establish an end-to-end win.
The load comparison is mixed (+2 input loads, -1 stack load/store in the hottest
whole body), so it does not establish the timing cause. Next examine the private
native Call ABI: keep the VM's three live pointer registers intact and address
captured arguments/private Output through its fixed host-stack layout. Retain
strict checking, original artifacts, guards, faults and transaction accounting.
[Width primary](../results/scalar-width-aliases-screen-token-01/ASSESSMENT.md),
[static loads](../results/scalar-width-aliases-screen-token-01/load-observations.json).

Follow-up after the private Call ABI primary: the suggestions file is unchanged.
Keeping x0–x2 live passes 597 workspace tests/profile, 21 focused controls, 121
strict commands and six exact original profiles. The 40-command primary fails:
wall 0.994813, CPU 0.968224, A/A wall 0.016892, wall margin 1.011705. Park it
without a larger comparison. Descriptive execution is 68.4 ms lower while Cargo
is 103.4 ms higher; these nested stages neither add nor establish a cause.
Next census zero-byte results and invariant successful-path step counts before
changing private Call commit traffic. Keep runtime/compiler ownership separate,
strict checking, two workers and the existing resource and timing gates.
[Private ABI assessment](../results/scalar-call-frame-abi-screen-token-01/ASSESSMENT.md).

Follow-up on September 14 after the private-transfer primary: independent saved-
body censuses identify fixed success counts, zero-byte results and 38.23 million
narrow argument captures in token block. The implementation passes 600 workspace
controls/profile, 23 focused controls, 121 strict commands and six exact profiles.
Its complete 40-command primary still fails: wall 0.986218, CPU 0.978075, A/A wall
0.036221, wall margin 1.022439. Park it and cancel larger comparisons. Descriptive
execution is 72.9 ms lower; the single profiled JIT compile counters differ by
only 1.6 ms in block and 4.4 ms in exhaustive token. Neither measurement is causal
or a substitute for the edited-source gate. Review remaining execution/general
Call costs before further private-body changes. No runtime adoption or new
compiler ownership follows.
[Transfer assessment](../results/scalar-private-transfers-screen-token-01/ASSESSMENT.md).

Follow-up on September 14 after fresh runtime sampling: the suggestions hash
remains unchanged. Two new unprofiled original-token executions pass, with nine
map/attribution controls and complete same-process generated-PC attribution.
Copy spans account for 487/1,814 generated self samples in block and 290/1,480
in exhaustive token; private scalar bodies account for 57 and 123. These partial
normal-entropy windows are diagnostic only. Follow the suggestions' remaining-
cost priority by reconstructing Copy subparts before another implementation.
Keep old failed general-address candidates parked, preserve compiler ownership,
and do not infer an end-to-end gain from sample shares.
[Fresh samples](../results/scalar-runtime-sampling-01/ASSESSMENT.md).

The fresh small-memory partition now reconstructs all 1,050/1,245 ordinary
functions and 60/69 scalar bodies exactly, with six focused controls and no guest
execution. Small Copy data loads contribute 171/98 samples; address selection
159/65. This does not justify repeating the failed selector/address rewrites.
Next census scratch-value availability at Copy loads, which the earlier Load-
only observer did not query. Preserve original source/destination checks and
full alias/clobber invalidation; no runtime change follows without coverage.
[Memory parts](../results/scalar-memory-parts-01/ASSESSMENT.md).

The Copy-specific scratch census passes 12 controls and reconstructs both fresh
captures without changing words. It finds 45/29 samples at candidate Copy load
instructions, versus 45/15 for the same captures' pre-address Load observations.
This justifies one bounded shared x9 cache experiment, with queries after address
handling and unchanged alias, clobber, fault, budget and profile contracts.
The combined 90/44 partial samples are not a timing prediction or adoption gate.
Use the unchanged primary-first workflow after correctness qualification.
[Copy census](../results/scratch-copy-census-01/ASSESSMENT.md),
[shared scope](../results/scratch-load-copy-coverage-01/ASSESSMENT.md).
