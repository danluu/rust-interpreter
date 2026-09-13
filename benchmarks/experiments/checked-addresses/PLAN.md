# Compact complete address checks

Base is main df8e5fa: the qualified operation-map/memory/lookup runtime and
integrated opt-in compiler diagnostics. The failed scalar Copy and budget
runtimes are absent. Their smaller code did not establish a full adoption or
new primary gain; do not repeat their timing campaigns.

Current main's generated samples attribute24.34%/18.26% to Copy and16.12%/8.02%
to Load in the two dominant token tests. The exact Copy8 audit includes182/77
checked-source-to-local samples. Check expansion is a bounded next mechanism;
those opcode percentages do not mean all its time is address validation.

Preserve both existing memory arenas and the actual heap tag1<<62. Combine
the original unsigned tag comparison with the existing heap-offset subtraction
using SUBS; retain every CSEL's original lo condition. Do not replace the rule
with a single-bit test: addresses above twice the tag still require the original
semantics. Omit only the unused readonly-prefix selection on reads.

For the complete remaining-length check, use SUBS remaining,length,address
and CCMP remaining,count,#0,hs before the common unsigned failure branch.
Subtraction underflow forces C=0, so a wrapped difference cannot pass the
count check. Counts below32 use CCMP's immediate encoding; larger constants
use a materialized register. Dynamic counts retain their existing register.
Keep null checks, readonly checks, zero-size bypasses, source-before-destination
validation, all-before-any-write copy behavior, every scratch/ABI obligation,
logical limits and cache invalidation unchanged. Apply the same range helper
to fixed-width and dynamic memory paths. No arena/layout/allocation change.

An eight-byte checked read takes6 words without heap support or12 with it,
down from9/17. Writes take8/15, down from11/19. Dynamic read/write paths share
the same new sizes. These static changes are not a latency prediction.
Platform assembly/disassembly was used only to verify instruction encodings;
the custom JIT emits the words directly and has no external backend fallback.

Expect451 workspace Rust tests per debug/release profile and one ignored.
New tests cover actual fixed copies across null, readonly, exact/overflowing
ranges, constant-size31/32 boundaries, both arenas, high-tag invalid addresses,
zero-size behavior and full backing bytes. Verify CCMP condition/default flags
and literal/register encoding boundaries. Existing dynamic-transfer, byte
comparison, fault-order, limit, ABI and memory-operand tests remain mandatory.

Build two Cargo workers under the shared lock,45-second admission and8GiB
per-command floor. Freeze source before execution. Compose the new VM with
the retained e729a493 exporter/wrapper pair (c1370fe6/cff204c5) used by baseline
d4a6ff9a, keeping frontend features outside this runtime treatment.

Before timing, require seven exact real selections, nine suites,203 strict
native/cache commands and three current profiles. Preserve exact per-PC work,
native transitions, memory/entropy and generated-map reconstruction. Code must
shrink on all three profiles. Then freeze a40-command token edit screen with
same-session baseline/duplicate, fixed anchor and ordinary native controls.
Keep all12 original assertions and five valid cumulative production edits;
only those five pairs enter the prospective gate. No repeat after failure.
A passing screen must precede a separately frozen full five-case comparison;
all full guards remain required for adoption.

The initial build caught an undercount of tag materialization in the new size
test: the existing immediate emitter uses two words, not one. All217 other
bytecode unit tests passed, including the new complete-range matrix. That
failed build remains recorded; only this size expectation and description
changed before the second build. The preceding Copy/budget full draft
remains unstarted. Keep other sessions' work and the paused goal state intact.
