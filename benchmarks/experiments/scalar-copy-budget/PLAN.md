# Scalar Copy plus shorter exact budget guards — qualification plan

The qualified current token sample assigns11.00%/6.79% of generated self-PCs
to region budget spans and24.34%/18.26% to Copy. Scalar Copy alone improved the
full token primary5.11% but failed the five-case adoption rule at Nushell's
noisy wall guard. Preserve that failure. Do not rerun the unchanged candidate.

Compose the already-correct scalar Copy mechanism with a new budget guard.
Every compiled straight-line region is statically bounded to1..1024 virtual
instructions. Replace mov(cost),cmp,b.lo,sub with subs-immediate,b.lo. The
unsigned borrow branch enters a dedicated fallback tail that adds the cost
back modulo64 before returning to the VM. No guest operation or profile hit
occurs on that branch. A successful region publishes exactly the existing
debit. Ordinary cursor memory remains untouched on the underflow branch;
resumable x22 is restored before the shared epilogue publishes it. Native
call/return charging is outside this change.

The immediate cost always fits12 bits; assert the region bound. Preserve
fault ordering, exhausted-budget tails, registers/ABI, profiling and all
compiled-code limits and reconstruction checks. Net static saving is one
word per region: two hot-path words removed, one cold restoration word added.
That static result is not a runtime speedup prediction.

Require the existing complete budget/ABI tests plus new direct fallback probes
at zero, below/exact/above region boundaries,1024-op regions andu64::MAX.
Inspect both ordinary and resumable modes, profiled/unprofiled and persistent
register configurations. The original scalar Copy tests remain mandatory.
Real qualification requires retained output, logical per-PC work, instructions,
peak memory, native call counts, fault results and emitted-map reconstruction.

Build the runtime from integrated main a2cb38c plus this candidate, expecting
456 workspace tests per debug/release profile and one ignored. Compose it with
retained exporter/wrapper tool e729a493261568d841d3ef212bcdfeef8fa4bf715cd26538f3cb9d1fa447e846
(exporter c1370fe6, wrapper cff204c5), matching baseline d4a6ff9a. This pair has
203 strict cache/Cargo checks and the full five-case adopted history. Main's
newer opt-in compiler features are outside the runtime benchmark treatment. No guest LLVM or alternate executor fallback.

Freeze a40-command changed-source token screen, current retained baseline and
same-session duplicate, fixed anchor and ordinary native. Keep the original
five edited pairs and all wrong/original/restored controls. Use the scalar Copy
screen gate unchanged; no repeats or post-hoc gate changes. If it passes, freeze
the full primary-first726-command five-case campaign, all guards mandatory.
Old scalar Copy timings are background evidence, never pairs in this campaign.

The source is implemented but unbuilt and unexecuted when this plan is frozen.
The observer/main correctness integration completed successfully before edits.
Qualify seven saved selections, nine suites,203 strict native/cache commands
and three current profiles before the screen. Require all original assertions,
logical work, memory/entropy, native transition counts and operation-map
reconstruction to match. Generated code must shrink for all three profiles.
Use explicit new candidate allowlisting; do not relabel the old scalar tool. Resource
checks,45-second lock admission, two Cargo workers and8GiB per-command floors
remain mandatory; recover sufficient owned completed cache space before any
large full comparison. The token diagnostic already rules out standalone lazy
MIR setup as a high-priority alternative: its measured upper bound is4.55ms.
