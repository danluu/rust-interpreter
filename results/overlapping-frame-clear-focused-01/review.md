Focused qualification CLOSED: ten exact tests in each of debug/release passed,
including526288 native clear executions (259 payload choices,127 total padding
choices across seven alignments,16 host offsets), full dirty-byte canaries and
all live call registers. Independent model covered122016 eligible byte ranges,
ten eligibility boundaries and two missing-hypothesis counterexamples.
Expanded existing VM fixture exercises112 layout combinations, repeated dirty
backing/retained padding, persistent modes, exact instruction/peak memory and
instruction/memory/frame limit boundaries against the interpreter. Existing
fixed-clear, arbitrary-prefix, large-frame and protocol partition controls pass.
Setup was24.32848 s wall,36.19442 s child CPU; these are qualification costs.

Production diff is confined to the ordinary clear_call_frame selection. Existing
static-empty proof runs first. New stores require validated A<=16 and A<=P<=256;
the preceding overflow/capacity/working-budget admission is unchanged. First range
lengthP and finalA-byte tail overlap for every0<=p<A; neither touches spare bytes.
AArch64 STP offset-16 and STUR offsets-2/-4/-8 operate on ordinary unaligned memory;
the native fixture covers all16 host offsets and exact prefix/suffix canaries.
No instructions update x0-x8, x16/x17, x19-x29 or budget. x3 already holds full new
logical end. x11/x12 scratch endpoints survive this path; subsequent peak logic
loadsx9 and resets flags, and argument addressing reloads its endpoints. Existing
fallbacks retain their original contracts. Scalar clearing is unchanged. Stores
still precede argument copies, preserving aliases into the new frame and padding.

The hot P40/A16 helper is four stores versus the original13-word padding sequence
plus three fixed stores. It always emits12 fewer words per eligible ordinary call.
No runtime branch, new option, cache identity shortcut or checking relaxation.
Correctness and code-size evidence do not establish an end-to-end speedup.
Proceed with full workspace validation, recorded-entropy original assertions and
prospective real changed-source screen. No default adoption yet.
