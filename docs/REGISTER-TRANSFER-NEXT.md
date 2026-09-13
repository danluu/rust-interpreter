# Register transfers after the indirect-call comparison

The paired-transfer candidate completes all 462 expected edited-command
outcomes. Token gains only 0.71% wall, below 1.77% A/A; both held-out guards
pass. Keep the candidate experimental without retiming.
[Complete comparison](../results/paired-registers-complete-01/assessment.md). It preserves the wide-operation runtime's VM counts and
native regions, retaining both 64-bit words of every register transfer. Static
generated size falls on the three current profiled artifacts and seven saved
unprofiled qualification artifacts. Neither observation establishes latency.
[Qualification](../results/paired-registers-build-01/assessment.md),
[current profiles](../results/paired-registers-profile-01/assessment.md),
[unprofiled size](../results/paired-registers-code-size-01/assessment.md).

Source review identifies two constraints for choosing subsequent work:

* The whole-function width proof in `jit/register_widths.rs` describes logical
  values. It is diagnostic and does not prove that a reused register's stored
  upper word is already zero. Native calls intentionally skip register
  clearing when `needs_initial_zeroes` proves that every read follows a full
  write. Omitting the upper write would invalidate that premise. Any narrower
  spill design needs a separate memory-state proof across fresh and reused
  frames, entry paths, loops and VM exits, and must count required initial
  clearing against saved traffic. The paired change needs none of that because
  both words are still written.
* `Assembler::address` already removes bounds checks for a known in-frame
  `Fact::Local`. Facts are currently local to the compiled region. A future
  diagnostic can count missed facts across region boundaries, using typed
  bytecode and the existing exact profiles. A whole-function fact requires
  every definition to agree and every read to follow a definition, or an
  equivalent bounded dataflow proof. Initial logical zero is not a frame
  pointer. Unknown definitions, conflicting offsets, skipped initialization
  and exhausted analysis budgets must remain unknown. First count eligible
  accesses that the current emitter actually checks; do not assume a useful
  opportunity from static local definitions alone.

The prior wider resident bank, larger local cache, lifetime allocator,
scalar-value ABI and address-check instruction shuffle remain recorded
experiments. Enlarged MIR optimization and inlining are already enabled in
the retained compute workflow. Repeating those settings is not a new design.
Finish the current complete comparison before selecting another emitter
implementation. No additional guest execution was used for this source review.
