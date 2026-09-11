Current checkpoint, 2026-09-10: **57a54edd is the retained experimental build**.
Its production VM/exporter binaries are exactly those measured as af9aa691.
The only subsequent source change corrects a new test's expected result and
comment; all 183 bytecode tests pass again. Local-memory forwarding reuses
available scalar values for exact proven local ranges, while preserving writes,
destination checks, final spills, budgets and strict rustc checking.
[Current report](results/local-memory-forwarding-01/summary.md).

All nine real source-edit/build/test workflows are complete: 25/45 commands
improve against 6bf, 30/45 against native, and 29/45 execution stages improve.
The four compute workflows win 14/20 complete commands and 19/20 execution stages.
Paired command savings are 279 ms for token, 56 ms for folded, 30 ms for SHA-1
and 7 ms for TLS. Preserve folded's 148 ms marginal-median regression, slower
individual commands, Ruff's 42 ms and larger Nushell's 33 ms paired regressions,
and all cold regressions. Native remains much faster on token and folded.
No timing correction or causal claim about Cargo is applied.

Qualification passes all 183 bytecode and 11 exporter tests, 47,004 native
differential commands, 245 TLS checks, and 382 fresh fre tests against fresh
native executions; seven fre tests remain ignored. All 63 new workflow artifacts
and every fre artifact match 6bf. Independent builds reproduce both production
binaries exactly. The original failed new-test comparison, all measured sources,
and all regressions remain preserved. Whole applications, actual unwinding,
general OS/FFI and threads remain unsupported.

Three diagnostic windows on the exact retained VM are complete. All original
token assertions pass with zero JIT declines, and all generated PCs are inside
the live arena of the same owned process. Of 7,715 samples, generated code has
37.0%, dispatcher self 29.0%, and frame reservation plus argument/result copies
26.8%. These partial windows keep original RNG and do not measure speedups.
Host call sites are verified against the current binary's own disassembly.
[CPU report](results/retained-token-cpu-sample-04/summary.md).

Next: use typed bytecode and the recorded execution profiles to count how much
callee frame zeroing is immediately overwritten by argument copies. Separate
proven local sources from unknown/indirect calls, and account for overlapping
argument slots. This is a feasibility census; no zeroing is removed. Any later
candidate must preserve initialization, alignment, argument order, memory limits
and fault behavior, then improve actual production-edit commands to advance.
Avoid rerunning parked register compaction, paired spills or fixed-register
residency without new evidence.

That census is complete: argument copies overwrite only 4.4% of proven local
frame bytes on folded and 9.1% on token, with 1.75 and 1.94 remaining zero ranges
per call. Park argument-only zero elision. The saved profiles contain roughly
42 GB and 32 GB of repeated frame clearing; inspect unused MIR allocations before
attempting a more complex runtime initialization policy. Scalar slot coloring
and bytecode inline-bank reuse already exist and must not be counted twice.
[Typed census](results/frame-initialization-census-01/summary.md).

The MIR inventory is also complete: all 11 exporter tests pass, fresh folded
and token bytecode match exactly, and original assertions pass. Unreferenced
MIR ranges account for only 1.46% and 1.78% of weighted direct-call frame bytes.
Display-name collisions between compiler shims are preserved and excluded;
none occurs among the weighted callees. Keep the existing frame layout.
[MIR inventory](results/mir-frame-census-01/summary.md).

Next, make the token workflow runnable entirely from tracked scripts and
validate that migration with actual edits. Then improve repeated per-edit
controls and native comparison coverage before another performance decision.
A typed census of remaining fully native leaf calls will guide the next larger
runtime experiment. The new user-owned suggestions.txt is review input; its
claims require verification and it remains unchanged.

Git now records the baseline and ongoing source/report changes. Build caches,
private checkouts and raw private evidence remain local. All builds, tests,
benchmarks and cleanup remain serialized. Only processes created for this task
may be controlled. Earlier checkpoints below describe historical states.

Historical checkpoint before local-memory forwarding: **6bf10fda**.
It combines restricted MIR scalar promotion, entry-register initialization
proofs and move forwarding with the packed native register cache. The exact
qualified source is integrated; f45 remains archived as the previous reference.
[Current report](results/scalar-packed-cache-01/summary.md).

All nine fresh source-edit workflows are complete: 30/45 full commands improve
against f45, 33/45 against native, and 34/45 execution-stage pairs improve.
The four compute workflows save paired command medians of 78 ms on folded trie,
175 ms on token-phrase, 98 ms on TLS and 47 ms on SHA-1. Native remains much
faster on token and folded. Larger Nushell regresses 558 ms, almost entirely
in Cargo; Ruff regresses 10 ms and private rg-aot 4 ms. Folded's cold sample
regresses 831 ms and TLS's 598 ms; other cold regressions remain in the report.
Earlier identical-tool variation does not erase or correct these measurements.
No general warm-compilation gain or whole-application support is established.

All 172 bytecode and 11 exporter tests, 47,004 native differential commands,
245 TLS checks and 382 freshly exported fre tests against fresh native controls
pass; seven fre tests remain ignored. All 63 new workflow artifacts and every
fre artifact match scalar81. Both combined binaries reproduce exactly from a
fresh source copy. The failed exporter-binary identity expectation, interrupted
first pgrust attempt, and standard-MIR device-stamp recovery remain preserved.
All five source pins are restored. Actual unwinding, general OS/FFI and threads
remain unsupported. Strict type/borrow checking and original assertions stay.

The function-wide register-residency diagnostic is complete. Its optimistic
best-four model leaves only 2.67% net register-transfer reduction after transition
costs, so that proposal is parked. A smaller paired-spill candidate passes 173
tests and exactly removes the predicted 70,452 folded native bytes, but wins
only4/10 real edited commands and none against native. Token regresses27ms and
folded25ms per command. It is parked without integration.
[Residency diagnostic](results/function-register-residency-observation-01/summary.md),
[paired-spill results](results/native-paired-spills-01/summary.md).

The unused-register census is complete. Monotone dense numbering predicts
539 million fewer address-generation instructions on folded trie, concentrated
in one original test routine crossing from2,197to2,031registers. Token-phrase
predicts only666,158 fewer instructions. These are typed estimates, not timing
results, and both artifacts remain unchanged.
[Register census](results/virtual-register-compaction-observation-01/summary.md).

The dense-numbering prototype is now parked. It passes 177 bytecode and 11
exporter tests, and all 14 fresh artifacts exactly match typed compaction of
their baselines, with complete inverse round trips. It wins only 4/10 actual
edited commands: folded regresses a paired 254 ms and token-phrase 33 ms.
Its added exporter pass takes about 4 ms and 18 ms respectively; these costs
do not explain every observed regression. Both noisy four-way runtime filters
and all original assertions remain preserved. No integration or broad
qualification followed. [Compaction results](results/virtual-register-compaction-01/summary.md).

A fresh retained-engine CPU sample verifies 1,017/2,485 stacks (40.9%) inside
the live generated-code arena. Dispatcher self accounts for 669 (26.9%), and
frame setup plus argument/result copying for 625 (25.2%). These are diagnostic
shares, not predicted speedups. The preceding unmapped sample is preserved.
[Current CPU evidence](results/retained-token-cpu-sample-03/summary.md).

The native-PC diagnostic is complete. All172 existing tests pass, all nine
artifact/run word audits match the clean emitter, and folded's full profile is
unchanged. Across three samples each, all1,082 folded and3,030 token generated
samples resolve to exact bytecode intervals. Scalar-load helpers contain35.3% and
28.7% of generated samples; checked-address helpers contain6.1% and7.8%.
Hot functions include production scan_upper_bounds and pointer precondition
checks. Generic test closures do not relabel their production callees as tests.
These distributions are diagnostic, without an instruction-latency or speedup
claim. [Mapped CPU evidence](results/native-pc-map-01/summary.md).

The isolated local-memory forwarding candidate `af9aa691` passes 183 bytecode
tests. It reuses available values for exact proven local ranges, invalidates
them on register overwrite/eviction and possibly overlapping writes, and keeps
all writes, checks, final spills and cache replacement order. Its typed census
reaches 246 million accesses in the saved folded profile and 659 million in the
token profile; these counts are not a speedup prediction.

All 32 saved-artifact runtime pairs improve across token, folded, SHA-1 and TLS,
including extra JIT generation time. Four actual source-edit workflows win14/20
complete commands against6bf and5/20 against native; execution improves19/20.
Token wins5/5 with a paired279ms saving; folded wins3/5 with a paired56ms saving, while its marginal
candidate median regresses148ms. Preserve that disagreement and both folded
command regressions. Token's cold command regresses63ms; folded improves137ms.
SHA-1 and TLS each win3/5, with paired30ms and7ms savings. All28 fresh artifacts
exactly match6bf; original assertions and all wrong-edit controls pass.
All11 exporter tests,47,004native differential commands and245TLS/callback
checks pass. Root6bf remains retained. Fresh fre coverage, remaining corpus
workflows and reproduction are still pending.
[Completed four-workflow evidence](results/local-memory-forwarding-compute-01/summary.md).
The current continuation state is
`.work/LOCAL-MEMORY-FORWARDING-CHECKPOINT-20260910.md`.

Cast-width, host-MIR and the other parked candidates remain isolated. Earlier
checkpoints below are historical, including statements that scalar promotion
was awaiting qualification or that f45/88 were current.

# Next work, guided by production edits

Current retained experimental build: `88c01c00d0fa5a0f4d93992af4a9cb3cfc815de8acab10b4628795bd77a07278`.

Native CompareBytes is integrated from the exact measured source. It validates
both complete ranges before reading, compares eight-byte chunks in lexical byte
order and handles short tails without overreading. Empty dangling ranges, usize
truncation, aliased registers, exact result encoding, the native register cache,
ABI, logical budgets and code-cap fallback are preserved. The exporter binary
and strict rustc frontend are identical to the parent.

All 165 bytecode tests, 47,004 native differential commands and 245 TLS checks
pass. At an explicit 150,000 allocation limit, all 382 non-ignored retained fre
bodies pass against 382 fresh native controls; seven tests remain ignored.
An additional 70 retained guest commands across five workflows in pgrust, Nushell,
Ruff and private rg-aot preserve 60 successes and ten wrong-edit rejections.
Those additional commands use historical native controls, without fresh exports
or performance claims. All five source pins are verified and restored.

Four actual five-edit workflows win 14/20 commands against the parent and 6/20
against native. Token-phrase wins all five parent comparisons, saving paired
301 ms per command and 244 ms in execution. Native remains much faster: medians
2.264 s native / 7.649 s parent / 7.378 s candidate. Folded regresses 19 ms per
command with effectively flat execution. TLS saves 60 ms mostly in Cargo; SHA-1
is effectively flat. All 28 artifact pairs are exact. The initial six-pair TLS
runtime regression of 2.8 ms is preserved. No broad warm-build gain is established.
[Complete evidence and cold timings](results/native-compare-bytes-01/summary.md).

Complete folded and TLS logical traces match. The exhaustive test's real-RNG
profiles differ slightly between processes; two explicit diagnostic RNG inputs
match all original assertions and normalized per-PC counts. Each emitter and
production RNG remain unchanged in that check. These are correctness results,
not timing evidence or universal trace equality. The original failed local-branch
relocation attempt and the lock preflight refusal remain preserved.

The allocation budget remains explicit: default 100,000 live allocations, maximum
one million, with a separate guest-byte budget. The exhaustive body peaks at
117,707 live allocations and 8,168,856 guest bytes. The preceding implementation's
roughly 10 ms interpreter regression remains documented.
[Allocation-budget results](results/allocation-budget-01/summary.md).

The guarded constant-copy follow-up is parked without integration. A diagnostic
finds 95.1% of dynamic copies are 24 bytes; a typed proof covers 94% of executed
copies. The isolated 169-test candidate reuses the existing native Copy emitter.
It passes focused traces and exact artifact checks, but wins only 6/10 complete
edit commands. Paired command savings are 31 ms on token-phrase and 6 ms on SHA-1;
execution saves 76/11 ms. Broader qualification was prepared but not run. Preserve
it as a working experiment rather than claiming a general development-loop gain.
[Parked copy experiment](results/constant-dynamic-copies-01/summary.md).

The redundant-memory-instruction candidate is also parked without integration.
A typed observer exactly reproduces retained machine code and identifies7.59B/
2.13B removable instruction executions in token-phrase/folded. The isolated
candidate removes exactly929244/381328 generated bytes and passes169 bytecode
tests, including all scalar widths, aliases, cache state, bounds, overlap and
budget tails. Folded logical traces match. Yet it wins only5/10 actual edit
commands and0/10 native comparisons: token-phrase regresses170ms per command
(execution saves11ms), while folded saves16ms (execution6ms). All14 artifact
pairs match. Broad native/TLS/fre and controlled-RNG gates were not run.
[Parked native memory experiment](results/native-memory-parts-01/summary.md).

A fresh retained-VM CPU sample now captures2554 stacks:1259 in generated code,
550 in unresolved dispatcher self, and602 (23.6%) in frame reservation and
argument/result copying.135 are in the exact return-copy call site. Mapping and
retained-binary disassembly substantiate the categories; sampled shares do not
predict speedups. [CPU evidence](results/retained-token-cpu-sample-01/summary.md).

Typed analysis of the same saved profiles finds21.2M/9.4M zero-byte returns in
token-phrase/folded, and proves caller-local destinations for all77.1M/17.1M
observed nonzero returns. Both isolated alternatives are now parked: skipping zero
result copies (167 tests), and additionally using safe slice copies for proved
local destinations (172 tests). Frame size remains48 bytes. The caller-local
version wins all12 token/folded runtime pairs, saving91/45ms with similar CPU
savings, but only5/10 actual edit commands and0/10 native comparisons. Token
saves49ms per command and75ms in execution; folded regresses14ms and4ms. All14
artifact pairs match. Broad and controlled-RNG qualification was not run.
[Call-result comparison](results/call-result-copies-01/summary.md).

Next quantify keeping non-addressed MIR scalar locals in VM registers. Existing
slot coloring changes frame layout but still emits loads and stores. A copied
typed exporter diagnostic must first establish eligibility and match exact
retained artifacts/profiles, accounting for call-ABI materialization and inlining.
No scalar-promotion implementation is started. Details:
`.work/MIR-SCALAR-PROMOTION-PLAN-20260910.md`.
The earlier next-step record remains preserved at
`.work/NEXT-AFTER-NATIVE-COMPARE-20260910.md`.
Archive: `.work/native-compare-bytes-experimental-88c0/manifest.json`.
Live progress: `.work/continuation-state.json`.

The following register-cache evidence describes the preceding retained build 87abb.

The block-local register cache is integrated from the exact measured source. It
keeps a complete dynamic 128-bit value in caller-saved x5/x6, spilling when needed
on eviction and at exits. Medium copies evict the cache before using that pair.
Bytecode, native block boundaries, instruction budgets, guest memory, frame
initialization, calls and strict rustc frontend behavior remain unchanged. A fresh
build of both tools exactly reproduces the measured immutable pair.

All 151 bytecode tests, 47,004 native differential commands and 245 TLS checks pass.
Replay of 389 retained fre bodies with 382 fresh native controls preserves 381
passes, the same allocation-capacity failure and seven ignored tests. Every passing
body has zero declined native functions; maximum generated code is 9,773,240 bytes.
The unchanged exporter permits exact retained-artifact replay; this gate did not
re-export all bodies.

The complete eight-workflow cohort wins 29/40 commands against 106eef and 29/40
against standard native Cargo. All fifteen folded-trie, TLS and SHA-1 edit commands
improve, saving paired medians of 157/67/99 ms, including 176/67/110 ms in execution.
Native wins every folded-trie and SHA-1 pair. Short Nushell and Ruff regress by
8/30 ms with nearly flat execution. Larger Nushell improves by 740 ms, including
756 ms in Cargo and effectively flat execution. The identical exporter does not
explain that Cargo variation. All 56 artifact pairs are exact, original assertions
are preserved, wrong edits are rejected, and all five source pins are restored.
[Complete results and cold timings](results/native-register-cache-01/summary.md).

The complete original folded profile matches. A typed compile-only observer
reproduces both measured native code sizes and counts register-array loads falling
from 1,161,857,638 to 189,948,735 and stores from 2,178,397,924 to 1,461,031,200.
These are generated LDR/STR instructions weighted by block hits, excluding guest
memory and hardware cache behavior; they are not CPU timing or DRAM traffic.
The six-pair runtime screen retains its initial folded regressions of 407/101 ms.

The wider fre replay recorded 54 bodies with cross-process statistic differences.
Repeated unchanged baseline runs reproduce variation while consuming host random
bytes. In isolated diagnostic builds, those same 54 bodies match original assertion
outcomes, all comparable statistics and sparse executed per-PC/block counts under
two identical explicit RNG inputs: 108 pairs, 216 fresh processes. Each executes
the mocked RNG and has zero declined functions. The production RNG and JIT emitters
are unchanged. This is correctness evidence, excluded from performance results;
two inputs do not establish universal trace equality. Failed wrapper attempts and
the private aggregate audit recovery remain preserved without timing reruns.

The allocation-budget follow-up above completes the count-cap investigation.
The preceding source and complete evidence remain archived at
`.work/native-register-cache-experimental-87ab/manifest.json`.

The preceding direct-call-return shortcut remains rejected: 151 tests and 504
exact outcome/profile cases passed, but only 6/15 complete edit commands improved.
The interpreter control improved without executing the shortcut; that cause
remains unresolved. [Rejected experiment](results/native-call-exit-01/summary.md).
The conservative memory-facts model found 1.74 million candidate loads among
416.38 million traced native loads. It misses some aliases and propagation; its
limited result did not justify implementing that pass.

The retained scalar-frame allocator preserves all 1,045 prototype slot plans and
fallback decisions while reducing isolated analysis cost from 19.919 to 7.033 ms.
It reduces the original traced direct-call frame volume from 46.219 to 42.539 GB
without removing initialization. Its eight-workflow cohort won 21/40 commands
against cd347 and 30/40 against native. Ruff and larger Nushell regressed mainly
in Cargo. [Scalar-frame results](results/scalar-frame-dense-01/summary.md).

Earlier native MIR controls found the then-current JIT lost all ten folded-trie
and SHA-1 edited commands to both stock and matching-MIR native. Matching-MIR
native won 8/10 against stock; all fourteen JIT artifacts and 28 native executable
snapshots were verified. [Native controls](results/native-mir-controls-01/summary.md).

Whole applications, arbitrary OS/FFI calls, guest threads and native unwinding
remain unsupported. No broad warm-build gain is established. No subagents or
unrelated process control; serialize builds, tests, measurements and eligible
completed-cache cleanup under `.work/benchmark.lock`.

The preceding retained cd347 CFG build won 20/40 commands against 57f3 and 30/40
against native. Larger Nushell improved warm commands by 1.354 s, mainly in Cargo,
but its cold run regressed from 72.001 to 106.371 s. The CFG pass took 3.937 ms;
frontend rose from 3.493 to 33.719 s and lowering from 77 to 2167 ms. These timings
do not explain the cause. Preserve that regression despite the current faster
cold sample. [Previous CFG results](results/cfg-single-copy-01/summary.md).

The following paragraphs retain the preceding experiments and their evidence.

Wide-integer candidate `81967134638a29bfec7ef37ee8b1addf3819e712007acb31fd5991efe68e13c7`
adds native 128-bit subtraction and comparisons. All 134 bytecode tests, broad
native checks, 245 TLS checks, and 381 retained guest passes are preserved. Its
profiles match all 4.448 billion logical instructions while removing 2.27 million
native entries. Tuned folded trie wins 4/5 complete edited commands, saving a paired
95 ms including 54 ms in execution. TLS is effectively flat (+3.4 ms paired).
All 14 bytecode pairs are identical; every wrong edit is rejected. Native still wins
all five folded-trie comparisons. The candidate archive and all raw data are retained.

The eight-workflow comparison across all five projects is complete: 20/40 command
wins against the parent and 30/40 against native, with all 56 artifact pairs identical.
Ruff regresses by 108 ms and larger Nushell by 302 ms in paired command time, mainly
in Cargo; both exporters are identical and execution is effectively flat. Keep the
regressions visible. This is a targeted runtime improvement, not a broad build-time
claim. [Complete results](results/native-wide-integers-01/summary.md).

The isolated pre-inline diagnostic now confirms the hot checked-add helper really
has a 520-byte frame, above the existing 512-byte eligibility bound. A smaller
change proved useful: forwarding before leaf inlining prevents expansion from
hiding identity wrappers. On the exact original folded-trie program, it removes
2,130,287 native entries and wins all six execution pairs (paired median -65 ms).
Static bytecode grows by 3,056 operations; native generation and peak guest memory
are nearly unchanged. This is a runtime screen, not edited-command qualification.

Candidate `57f31f5684651dacf24ff7da3d3de401adb552ac2208c44580a9fb24ed3757fe`
now applies forwarding before and after the existing bounded leaf pass. All 138
bytecode tests pass, including chain elimination, aliased results, indirect handles,
inlined diagnostics, recursive cycles and unchanged eligibility guards. Broad
compiler/native gates and all 245 TLS checks pass. Real folded-trie edits win 4/5
commands, saving a paired 62 ms (36 ms execution); TLS wins 3/5, saving 15 ms
(8 ms execution). Native still wins every folded-trie pair. Original-state artifacts
match the isolated probe exactly. Fresh export/execution coverage of all 389 fre
bodies is complete: 381 pass, one has the same allocation-capacity error, and seven
are ignored. All eight production-edit comparisons are complete. No frame limits were raised and no general non-leaf inliner was added.
Both actual tool binaries changed; the VM implementation source is unchanged.
[Current partial comparison](results/inline-order-01/summary.md).

The following notes retain the parent experiments and the evidence that led here.

Cached-readiness candidate `19139c68253653632fffbadee082ee5ff629e29874c1f41e1585f8d9f66eb7ba`
completes the lazy native generation follow-up. All 130 bytecode tests, broad native
checks, 245 TLS checks, and 381 retained guest passes are preserved. One ordinary
fre test reaches the existing 100,000-live-allocation cap; seven are ignored.
There are 382 fresh native controls in the retained-program replay.

Inlining the cached check improves all ten execution-stage pairs but only five
of ten complete production-edit commands. TLS wins 2/5 commands against its parent
and 5/5 against native; folded trie wins 3/5 against its parent and 0/5 against
native. All 14 artifact pairs are identical. Retain the change experimentally;
Cargo variation prevents a broad build-time claim.
[Completed comparison](results/lazy-cached-guard-01/summary.md).

With the same candidate, MIR3 plus an eightfold MIR inlining budget wins all five
folded-trie edit commands against ordinary MIR3. The paired saving is 428 ms per
command, including 369 ms in execution. It still loses all five native comparisons
(medians 3.077 s JIT / 1.883 s native). MIR defaults remain unchanged. A future
control should give native Rust the same MIR flags before comparing against the
best available native configuration.
[Completed MIR comparison](results/paired-folded-mir-inline8-01/summary.md).

The tuned profile executes 4.448 billion logical instructions, with 53.07 million
native entries. The 4.53 million interpreted Sub/Le operations are actual 128-bit
niche-discriminant checks, including a tag near `u128::MAX`; narrowing is invalid.
The resulting candidate adds full-width native subtraction and comparisons, preserving
bytecode, alias ordering, checked overflow, instruction budgets, and profiles.
First check against native Rust and the interpreter, then screen retained artifacts
and compare complete production-edit commands. Calls still dominate interpreted
operations; bounded multilevel leaf inlining remains a separate possible follow-up.

Direct forwarding now completes thirteen production-edit workflows: 37/65 command
wins against the prior JIT, 49/65 execution-stage wins, and 42/65 wins against native.
The new TLS-heavy workflow saves 204 ms per command, removing 10.47 million calls
without code/layout growth. The three changed-artifact compute workflows win 13/15
commands. The eight broader workflows win 16/40; Ruff and larger Nushell retain
98 ms and 264 ms paired regressions, mostly in Cargo. All 125 bytecode tests, broad
native suites, 245 TLS checks, and fresh 320/62/7 fre coverage pass. Every one of
91 artifact pairs was audited. Retain build `588cad897ac2dcee91ddb0982aebbf15db434b3e66297daf2d1cc4a47d294e52`
as an experimental runtime improvement; a broad build-time gain is not established.
[Complete comparison](results/paired-direct-forwarding-corpus-01/summary.md).

Earlier MIR coverage lowered all 389 fre bodies. Before lazy native generation,
320 passed and 62 reached the native-code cap; the new engine resolves 61 of those
62. The remaining failure is a separate allocation-count bound, confirmed at only
4.7 MB of live guest bytes. Raising the byte budget does not address it.
[Earlier MIR coverage](results/audit-execution-fre-mir-inline8-01/summary.md).

The following paragraphs retain earlier experiments and their decisions.

Native copies through 128 bytes completed twelve production-edit workflows:
38/60 wins against the prior JIT, with all 15 folded-trie/word64 pairs improving.
Broad native differentials pass, all 60 bytecode pairs match, and fresh native
controls preserve 303 passing original fre tests. SHA-1 and frontend-heavy
commands are mixed. The larger Nushell command regresses 659 ms in the median
paired comparison, mostly in Cargo; execution differences are below 3 ms and the
exporters are identical. Retain this as the experimental baseline for the next
change. Native still wins all 20 compute comparisons. The CPU-query branch and
the historical qualified reference remain distinct; the launcher uses the current
working tree unless `--tool-key` selects an immutable build.
[Full comparison and retained regressions](results/paired-native-medium-copy-corpus-01/summary.md).

Scratch-frame reuse passed 1,014 focused native checks, both 23,502-command
native suites and the other compiler/runtime gates. It won 19/24 real-artifact
execution pairs but only 10/20 complete edited commands. The inlined word64
workflow lost all five pairs, mostly in Cargo. This does not establish a causal
allocator regression, but it does not satisfy the end-to-end selection criterion.
The change was set aside, its source/binaries/evidence archived, and the prior
copy-emitter source and binaries explicitly rebuilt to identical hashes.
[Full-command decision](results/paired-temporary-frame-compute-01/summary.md).

Raising leaf body, argument and result copy limits to 128 bytes passed 99 bytecode
tests and broad native gates. It won 17/24 execution-only pairs but 12/20 complete
edited-command pairs. Folded-trie lost 4/5, with a 128 ms median paired increase;
its execution-stage median also worsened by 33 ms. All five SHA-1 artifact pairs
were identical, so their four timing wins do not demonstrate an execution-code
gain. The wrapper's changed-bytecode assertion failed only after all four
benchmark subprocesses completed; every retained hash and source pin was then
verified without rerunning timings. Keep this variant unqualified.
[Full-command evidence](results/paired-native-medium-leaf-compute-01/summary.md).

The profile found a concrete frame cost: an unexecuted error helper is inlined
into a function called 5.94 million times, growing each frame from 520 to 848 bytes.
The guarded variant limits extra frame space for newly eligible aggregate leaves
to half the original caller frame, including alignment padding. Existing
small-copy eligibility remains. All 101 bytecode tests and broad native gates pass.
It wins 10/15 changed-bytecode edited-command pairs; the five byte-identical SHA-1
controls win 3/5. Folded-trie saves 25 ms and improves every execution-stage pair;
word64 saves 36 ms, and inlined word64 saves 9 ms. The smaller gains remain sensitive
to variation. Fresh controls preserve 303 passing fre tests and all 389 classifications.
The full twelve-workflow corpus is complete: 35/60 command wins and 30/47
changed-bytecode wins. Ruff and larger Nushell regress by 145 ms and 556 ms in
median paired command time, mainly in Cargo. Broad performance is not qualified.
There are no function-name or project-specific rules in the guard.
[Guarded comparison](results/paired-native-medium-leaf-frame-guard-corpus-01/summary.md).

The identical-tool control now completes fifteen real production-edit pairs.
Both VM and exporter binaries, executed artifacts, source edits and test selections
match within every pair. Nominal median command differences are -10 ms for fre,
-17 ms for Ruff and -724 ms for larger Nushell; Nushell's individual differences
range from -2.07 s to +2.14 s. This is evidence of substantial variation, not a
universal noise threshold or an explanation of the other experiments' regressions.
Do not subtract control medians from optimization measurements.
[Control results](results/identical-tools-aa-e2e-01/summary.md).

The actual scratch-frame comparison was repeated across all four original compute
workflows, using the retained cd9 baseline and 67b3 candidate. The repeat wins
12/20 complete commands; keeping the prior twenty pairs gives 22/40 command wins
and 33/40 execution wins. Folded-trie execution improves in all ten pairs, but
inlined word64 retains a 13 ms combined median command regression despite its
5 ms execution saving. These modest, mixed command results do not justify a
source restoration or broader qualification now. Keep scratch reuse archived;
the original 0/5 inlined-word64 outcome alone is no longer the decision basis.
Explicit `--candidate-tool-key` selection left the guarded working tree unchanged.
[Both actual runs](results/paired-temporary-frame-recheck-01/summary.md).

Empty unit-call removal was implemented and tested, then archived. It wins 11/20
complete production-edit pairs; folded-trie execution saves 26 ms but the command
saves only 2 ms in the median paired comparison. Word64 and inlined word64 remain
mixed. All 106 bytecode tests and broad native checks pass, but the command results
do not justify further qualification. The guarded source and both rebuilt binary
hashes are restored exactly. Both actual VM binaries differed in this experiment;
a separate crossed screen retains both artifact/VM combinations.
[Empty-call results and decision](results/paired-empty-unit-call-compute-01/summary.md).

The guarded traces reveal another concrete interpreter boundary: population count
is excluded from native unary operations even for 64-bit inputs. SHA-1 interprets
2,033,159 such operations, each word64 workflow 324,264, and folded-trie 78,642.
The native population-count experiment is now implemented, with 128-bit fallback,
exact budgets and register preservation. All 104 bytecode tests and broad native
checks pass. Its identical-artifact screen wins 19/24 pairs: word64 and SHA-1 improve,
but folded-trie regresses by 27 ms. The four production-edit workflows are now
complete, with 14/20 command wins. SHA-1 improves all five commands and execution
stages, saving 27 ms and 19 ms by paired medians. Folded-trie is effectively flat;
word64 command savings are mostly in Cargo. The full twelve-workflow corpus is
now complete: 37/60 command wins against the prior JIT and 44/60 against native.
Larger Nushell varies by seconds while its execution change is submillisecond;
Ruff retains a 12 ms paired command regression. This does not establish a broad
opcode-driven speed gain. Fresh fre native controls preserve all 303 passing
tests and all 389 classifications. Retain this as an experimental baseline for
the next separately measured dispatch change.
This is a general opcode extension; profile names never select compiler behavior.
[Full corpus comparison](results/paired-native-popcount-corpus-01/summary.md).

The native-exit dispatch change is now implemented experimentally. After generated
code returns, the VM checks its remaining budget and enters the existing interpreted
dispatch directly. Native successors already link within generated code. All 107
bytecode tests pass; the runtime screen wins 23/24 pairs with identical guest work
and complete profiles, saving 124 ms for folded-trie and 69 ms for word64. Broad
native validation passes. All twenty compute edit commands and execution stages
improve against the population-count build, using both actual exporters and VMs.
Paired command savings are 94 ms, 68 ms, 58 ms and 9 ms across the four workflows;
all bytecode pairs are identical. Native still wins 18/20. Fresh native controls
preserve all 303 fre passes and all 389 classifications. All twelve workflows
are complete: 39/60 commands improve against the prior JIT and 42/60 beat native.
The eight broader workflows win 19/40; Ruff and larger Nushell retain 180 ms and
383 ms paired command regressions, mainly in Cargo. Retain the VM change as the
experimental baseline without claiming a broad build-time improvement.
[Complete corpus and decision](results/paired-native-exit-dispatch-corpus-01/summary.md).
[Complete compute comparison](results/paired-native-exit-dispatch-compute-01/summary.md).
[Dispatch screen](results/native-exit-dispatch-real-screen-01/summary.md).

The guest allocator/TLS capability now runs all 17 prior fre runtime failures.
Fresh native controls give 320 passing bodies, 62 lowering blocks and 7 ignored.
The implementation executes Rust's own destructor list and thread cleanup through
guest callbacks; it preserves original test instrumentation. The new explicit
try-callback option executes only the normal-return path, retaining command failure
for actual panic/unwinding and faults. Strict type/borrow checking remains enabled.
119 bytecode tests and staged native allocator/TLS controls pass. The current
production-edit benchmark uses the 17 newly enabled original tests, with five
production changes and an incorrect-edit control. The JIT loses four of five warm comparisons (median commands 2.42 s JIT, 1.88 s
native). Profiles identify 40.54 million interpreted calls in the edited batch;
bounded inlining across call chains is the next candidate. Broad regression gates passed; keep the completed dispatch result as the
performance comparison baseline.
[Capability and edited commands](results/guest-tls-capability-01/summary.md).
[Fresh execution coverage](results/audit-execution-fre-guest-tls-01/summary.md).

The paragraphs below retain the prior qualified decisions and history.

The latest coverage change adds 11 passing original fre tests using the explicit
unavailable-call option, with strict type and borrow checking. Their full-command
workflow reproduces a warm regression at default MIR. Explicit MIR3 then wins
all five paired production edits against MIR1 and native, saving 358 ms per
command versus MIR1 by the median paired difference. Keep MIR tuning explicit:
this is one tested workflow, with a 127 ms cold-command cost relative to MIR1.
[Current evidence](results/unavailable-calls-capability-01/summary.md).

Metadata-sensitive wide-pointer equality now passes focused and broad native
checks and a five-edit real workflow. All 327 prior artifacts remain identical;
the other 62 bodies advance to the 10,000-instance expansion limit. It adds no
passing original tests yet. [Evidence](results/wide-pointer-capability-01/summary.md).
The next runtime blockers are actual CPU-feature queries (62 bodies) and TLS
destructor registration (16). Returning invented feature flags or acknowledging
registration without destructor behavior would invalidate the comparisons.

The following sections retain the preceding experiments and their decisions.

The selected native block-linking implementation passes the nine-workflow corpus
and all 15 paired production-edit comparisons. Complete-command gains are
438 ms for default word64, 316 ms for inlined word64, and 189 ms for SHA-1.
The paired native controls still win those compute workflows. Interpreter
performance is approximately unchanged. The large-project workflows remain
dominated by Cargo/frontend work.
[Current results](results/e2e-jit-region-linking-corpus-01/summary.md),
[paired comparisons](results/paired-region-linking-e2e-01/summary.md).

## Reduce budget bookkeeping inside native chains

The first variant held the remaining budget in x20 and saved four registers on
a 32-byte frame. It passed all correctness checks but was rejected after 60
controlled runtime commands: both word64 JIT cases won only 2/6 pairs, and the
interpreter controls regressed. No full-command qualification was run for it.
[Negative result](results/jit-region-budget-register-runtime-01/summary.md).

The second variant saved only x19/x20 in a 16-byte frame. It passed the same
correctness gates and 60 runtime commands, then lost all ten paired word64 edits:
median paired increases were 55 ms and 19 ms. SHA-1 was essentially unchanged.
Both budget-register variants were rejected. The qualified block-linking source
and both release binaries were restored exactly; the five source pins are clean.
[Full-command rejection](results/paired-region-budget-leaf-e2e-01/summary.md).

Keep the budget in the host cursor for now. Broader execution coverage is the
next substantial direction.

## Turn lowering coverage into broader execution evidence

Nushell's retained audit now saves 162 validated programs out of 279 discovered
bodies; 117 remain blocked. The pack contains 208,783,957 bytes. Serialization,
hashing, and writing took 0.53 s; launcher verification took 0.08 s in a 68.3 s
fresh command. This is diagnostic collection, with no guest execution.
[Real collection](results/lowering-audit-nushell-retained-01/summary.md).

Built-in metadata and retained artifacts now pass 79 focused native/VM commands,
99 launcher checks, and 23,502 native regression commands. The VM is identical
to the qualified block-linking build. [Usage and evidence](AUDIT.md).

The fre survey classified all 389 bodies. All 198 lowered ordinary tests agree
with fresh native controls, after explicitly retrying nine instruction-limited
cases. The remaining 191 are lowering-blocked, including all seven ignored tests.
The largest passing case executes 17 billion instructions and takes 11.084 s in
the JIT versus 0.541 s natively: runtime remains a substantial limitation.
[Combined survey](results/audit-execution-fre-combined-01/summary.md).

The complete 17-test grapheme module now passes real production edits: native
1.378 s, interpreter 0.857 s, JIT 0.806 s. An initial continuation-byte mutation
passed both native and JIT because the original tests do not expose that bug;
the rejected run is preserved. The benchmark now mutates the exercised ASCII
path and keeps all original tests unchanged.
[Production workflow](results/e2e-workflow-fre-grapheme-scalar-dfa-02/summary.md).

The table lookup now passes native hardware checks and adds 29 passing fre
bodies. Of the previous 198, 41 with changed bytecode were rerun successfully;
157 retain identical bytecode and VM hashes. Total retained execution evidence
is 227 ordinary tests; 162 remain blocked. The six-test packed-literal workflow
passes five production edits and its negative control: 1.508 s native, 0.971 s
interpreter, 0.951 s JIT. Its seventh regex-reference body is still blocked.
[Evidence](results/simd-table-capability-01/summary.md).

Ordered integer SIMD sums/products now pass the same broad checks, including
initial accumulators, signed lanes and 128-bit lanes. They add four passing fre
tests; two other bodies now reach synchronization calls. Current retained
execution evidence covers 231 ordinary tests, with 158 lowering-blocked.
[Reduction evidence](results/simd-ordered-capability-01/summary.md).

The expanded eleven-workflow corpus now passes on this frozen build, including
an isolated SHA-1 rerun after a cleanup overlap. All five source pins are restored.
[Current corpus](results/e2e-simd-coverage-corpus-01/summary.md). Saved
profiles now put the safe short-block bridge idea at only 823,038 executed
instructions in word64-inline8 and 476 in SHA-1. Block reconstruction matches
all compiled endpoints. This is a coverage screen, not timing evidence; the
idea is deprioritized. [Analysis](results/short-native-bridges-analysis-01/summary.md).

Scratch x9/x10 reuse passed 77 bytecode tests and every correctness gate, but
won only 6/15 paired complete commands. Default word64 lost all five pairs
(+37.609 ms median paired change), inline8 saved 7.008 ms, and SHA-1 was nearly
unchanged. The candidate was rejected and the exact qualified source/binaries
restored. [Full-command evidence](results/paired-temporary-reuse-e2e-01/summary.md).

A fresh one-second CPU sample still shows substantial host dispatch, frame
reservation/zeroing, and copying. Saved traces classify 8.68 million word64-inline8
calls and 2.42 million SHA-1 calls as leaves using supported native operations
plus return/trap; earlier straight-line classification missed branching leaves.
These are call counts, not CPU-time or implementation guarantees.
[CPU profile](results/word64-linked-cpu-profile-01/summary.md).

Keeping each host engine/profile loop in a separate function also passed all
correctness gates, but was rejected after 60 runtime and 15 complete-command
comparisons. It won 6/15 full-command pairs; word64 interpretation lost all six
runtime pairs (+557 ms median paired change). Four distinct host loop symbols
were verified, so the intended structural change occurred without a useful
overall performance result.
[Evidence](results/paired-split-engine-loop-e2e-01/summary.md).

Bounded bytecode leaf inlining is now an opt-in exporter experiment. The first
prototype lost all 18 JIT runtime pairs: adding branches caused conservative
whole-caller register clearing. Restating proven Local addresses before copies
and at return joins eliminated that extra clearing in the three saved programs.
The revised screen won 17/18 JIT pairs, while interpretation regressed slightly.
Those runtime measurements exclude transformation and frontend cost; shared-host
timing was particularly variable for inline8 and SHA-1.
[First prototype](results/leaf-inline-runtime-01/summary.md),
[revised screen](results/leaf-inline-runtime-02/summary.md).

The integrated `--inline-leaves` option is disabled by default. Cargo tracks it
as an exporter input, and older retained tools reject it. The pass uses static
selection, disjoint per-caller storage, ordered argument copies, per-invocation
frame initialization and a common result copy. It preserves cold checks and
function handles. Code, frame, register and diagnostic growth are bounded;
expansions that newly require whole-caller register clearing are skipped.
The resulting artifact has different instruction and memory requirements.
The option passes 84 bytecode tests, 24 option/cache/source-edit checks, all
existing correctness gates, and 23,502 native comparisons with it enabled.
All eleven production workflows pass, with 35/55 complete-command wins; the
mixed results do not justify enabling it by default. The word64 and SHA-1
execution gains are clearer than the shorter workflows, where Cargo variation
dominates. All 231 supported ordinary fre bodies agree with fresh native runs;
158 remain lowering-blocked. The candidate is retained as an opt-in experiment,
and the `0d0d` baseline remains available.
[Full comparison](results/paired-leaf-inline-corpus-01/summary.md),
[fresh execution coverage](results/audit-execution-fre-leaf-inline-01/summary.md).

Direct native stores for small, proven local `FillBytes` operations are retained.
They preserve region splits, live registers, exact budgets, aliases and bounds.
The same-artifact runtime screen wins all 18 inlined-bytecode JIT pairs. After
fixing randomized function-pointer body scheduling, the repeated production-edit
comparison wins 14/15 compute commands and all 15 compute execution stages.
Native remains faster on compute. The full eleven-workflow comparison wins
39/55 commands, with small and frontend-heavy changes mixed.
Leaf inlining stays opt-in. A fresh collection and fresh native/JIT execution
again agree on 231 ordinary fre tests; 158 remain blocked.
[Complete comparison](results/paired-jit-local-fill-corpus-02/summary.md),
[runtime screen](results/jit-local-fill-runtime-01/summary.md),
[deterministic export](results/export-determinism-01/summary.md).

The original Ruff attempt stopped at artifact equality. The original Nushell
type-relations attempt stopped when native rustc received SIGTERM; its sender
is unknown. Both failures are preserved. Ruff passed with the ordering fix;
Nushell passed its entire retry with fresh caches. Partial timings are excluded.

Existing instrumentation puts JIT construction at only 0.7–11 ms in the current
workflows, so persistent machine-code caching is a lower priority than execution
and frontend costs. The unavailable-call experiment described above now separates
unexecuted semaphore paths from reached CPU-query and TLS-registration boundaries.
Its 11 new passing bodies do not constitute general synchronization support.

Retained audit bodies can now be replayed with a separately identified immutable
VM; original collection provenance remains independently checked.
[Replay usage](AUDIT.md). Native call chaining, synchronization, TLS destructors,
and custom harnesses remain alternate directions.

## Measurement and checking policy

Use complete commands after real production edits as the primary decision metric.
Keep unchanged builds as correctness checks. Pair baseline and candidate commands
with independent caches, identical selections, and preserved executed bytecode.
Record Cargo and execution stages, include setup/cold costs explicitly, retain
all samples, and preserve source pins. Run workloads serially on a frozen build.
Shared-host variation remains visible in the reports.

Keep ordinary type and borrow checking. The earlier Ruff profile measured about
1.008 s in macro expansion, 0.223 s in type checking, and 0.066 s in borrow checking;
these instrumented timings are nested, not additive totals. Lazy borrow checking
would address little of that measured latency while changing diagnostics.
[Frontend evidence](results/frontend-profile-ruff-01/summary.md).

The standalone population-count experiment is a useful negative result:
correctness checks passed and SHA-1 improved, but both paired word64 commands
slowed. Its source was reverted before block linking was implemented.
[Rejected candidate](results/paired-popcount-e2e-01/summary.md).

Earlier experiments and their original measurements remain in
[runtime history](RUNTIME-HISTORY.md) and [JIT history](JIT-HISTORY.md).

The restricted MIR scalar-promotion candidate remains isolated. Its first
version reduced executed bytecode but introduced expensive register clearing;
the final 81e014 variant adds an entry-initialization proof and forwards proven
redundant scalar moves. It preserves captures across overwrites and block
boundaries, strict Rust checking, and the custom guest engine.
[Scalar promotion evidence](results/scalar-promotion-01/summary.md).

All nine original workflows are complete: 27/45 edited commands are faster than
retained88 and 31/45 faster than native. The two runtime-heavy fre workflows win
9/10 against retained, but native remains faster in all ten comparisons. The
candidate passes 168 bytecode tests, 11 exporter tests, 47,004 native differential
checks, and 245 TLS/callback checks. Fresh fre exports pass all 382 active tests
against fresh native executions; seven tests remain ignored and no passing case
declines native compilation because of code capacity.

Larger Nushell needs investigation before integration. Its first five-edit run
regresses by a paired 378.2 ms, mostly in Cargo, while the new pass takes about
2 ms. A same-order independent repetition gives −136.1 ms; a third run with each
positive edit's mode order reversed gives +101.8 ms. All seven baseline and
candidate artifact pairs match across all three runs. Preserve all three runs;
the ordering association does not establish the cause of the variation.

The completed diagnostic records 19 rebuilt units per edited command. In its
largest regression, 1.04 s of the 1.30 s command difference occurs before the
selected test target starts. Child CPU increases by 0.23 s, while its reported
major-fault counter rises by 51,786. This localizes variation outside the new
pass without establishing its cause. All seven artifact pairs match again.
[Instrumented diagnostic](results/scalar-promotion-cargo-diagnostic-04/summary.md).

Keep scalar promotion isolated. The next bounded experiment starts from retained88
and avoids forced guest MIR retention in native host libraries only when Cargo
explicitly separates host and guest targets. Ordinary checking and native build
scripts/macros stay intact; guest libraries retain MIR. Native host nu-protocol
has a 1.90 s median unit duration in the diagnostic baseline, with overlap, so
there is a measured cost to investigate but no demonstrated saving. Require the
original five-edit Nushell comparison, fresh native controls and identical guest
artifacts before broadening this candidate. Root88 remains retained; selected
library tests do not establish whole-application support.

The host-MIR candidate85f816 passes its initial checks and preserves all seven
guest artifacts, but its first edited-command screen wins only 2/5 against
retained (+219.4 ms paired). Cold time falls from 67.662 to 65.502 s, and native
host metadata shrinks 20.6%; neither establishes an edited-command improvement.
Keep it isolated. Its large per-edit swings resemble the earlier scalar runs.
The next control runs identical retained tools in both custom slots with separate
Cargo caches, the original five real edits, and original mode order. Shared
binary paths are an explicit limitation of that control. Preserve all earlier
results; the control measures variation without claiming an optimization.
[Host-MIR experiment](results/host-mir-retention-01/summary.md).

The identical-tool control is complete: +181 ms median slot difference and up to 1.68 s per edit, with identical binaries and all seven guest artifact pairs. The timing pattern appears without a code change. Before further candidate decisions, evaluate consecutive full edit sequences per engine and reverse phase order in a separate run. Keep all setup, cold costs, wrong-edit rejection and original assertions. This tests a measurement change; it does not establish a cache mechanism or erase the prior results. [Control](results/identical-tool-control-01/summary.md).


2026-09-10 resumed: reverse trajectory interrupted during native cold build (Cargo101, rustc SIGTERM, source unknown). Original records/assertions retained; source restored. Completed fourteen custom commands independently audited in results/identical-tool-trajectories-interrupted-01: identical tools4/5,-284.372ms versus forward0/5,+1141.428ms. Grouping has not eliminated variation; no correction applied to candidate results. Root88 remains retained; scalar81 and host85 isolated. Next isolated hypothesis: pack two known-zero-high-half dynamic VM values into existing x5/x6; full-width values retain both registers. Preserve all guest checks/region/budget semantics, then use real runtime-heavy edit workflows.


Packed native cache f45d758b now passes169bytecode tests and its first two real-edit workflows: token4/5,-221.587mscommand/-157.994msexecution; folded5/5,-59.010mscommand/-30.927msexecution. All10execution stages improve; native wins all10. All14RBCpairs exact retained; source restored. Public results/packed-native-cache-01. Broader native differential checks now running; no integration. Exits continue spilling dynamic cached values because the existing native ABI tests observe final register slots (JIT.md), so do not casually remove those stores using bytecode-only liveness.
