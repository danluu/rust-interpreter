# Broader aggregate storage after the native-call and inlining comparisons

The [current sample split](../../../results/register-clearing-attribution-01/assessment.md)
puts every observed clearing sample in guest memory. The [MIR policy comparison](../../../results/mir-call-policy-01/assessment.md)
rejects ordinary inlining: folded wall +4.55%, token +6.88%, with higher CPU.
Keep the current enlarged inlining policy and exact 0e runtime. No register-zero
optimization, primitive-array rerun or intermediate inlining sweep is selected.

The old inventory classifies most of the hot frames as `other_layout`. In the
hottest folded function, 16,704 of 18,224 frame bytes are MIR local storage;
412 nonprimitive physical ranges account for 16,422 bytes. The earlier private
primitive-array scope excluded these ranges and almost all Call destinations.
The new question is whether **complete byte writes** make broader private
aggregate ranges safe to share across disjoint lifetimes.

Start with a diagnostic observer of the actual checked MIR and emitted bytecode,
using the retained scalar-coloring planner and an independent certificate. Keep
production slots, bytecode, initialization and runtime unchanged while measuring
scope. Record types/layouts, physical slots, exclusions and exact compiler
instance IDs. Never select functions by project, name or observed hotness.

- Distinguish complete writes from partial writes. `Rvalue::Use` lowers to a
  full-size Copy, while Aggregate assignments can leave padding or inactive
  enum bytes untouched. A complete MIR destination is not itself proof that
  all its bytes are overwritten. Derive the coverage from the actual lowering
  or a narrowly reviewed lowering rule, including size and projection bounds.
- Preserve incoming whole-slot liveness for partial writes and uncertain
  coverage. Full copies include padding; the source must retain its original
  initialization. Dead writes must interfere with other live values too.
- Treat Call results on their normal-return edge. Keep exceptional outcomes
  separate. Do not classify every MIR Call as a full write: some calls lower
  to intrinsic field stores rather than a bytecode Call/result Copy. Require
  the actual lowering classification before killing destination liveness.
- Exclude ABI storage and every address-taken/escaping or unclassified range.
  Reading a pointer local through Deref is not a write to the pointer's own
  slot. Walk index operands and source projections as well as destinations.
  Any uncertain alias declines reuse; it does not justify skipping a check.
- Compare against reconstructed current physical slots, not an uncolored
  layout. Keep current primitive coloring and inline-bank reuse in the control.
  Bound CFG, byte-coverage and interference work; record conservative declines.

Qualify partial stores, untouched enum bytes/padding, full Copy, address escapes,
dead writes, loops, joins, and Call success/failure using independent byte-state
examples. Fresh observer exports must preserve original artifact hashes and
assertions. Reuse prior exact-artifact execution counts only with an explicit
historical label and complete typed identity/count validation; collect new
counts if a required identity or path distribution cannot be established.

A proposed compiler transformation needs at least 25% additional weighted
direct-frame-byte scope on folded before implementation, an explicit byte and
alias argument, and no claiming sampled time as predicted savings. Then
predeclare a changed-artifact E2E comparison requiring at least 10% folded
wall improvement with lower CPU and no more than 5% token wall/CPU regression.
Keep the complete native/assertion controls and subsequent seven held-out and
broad execution qualifications. If the scope remains small, park it and move
to the separate unfiltered-suite compatibility direction; do not tune clearing
loops again.
