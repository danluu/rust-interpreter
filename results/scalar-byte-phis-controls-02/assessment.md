# Contiguous byte-phi controls pass

All 348 bytecode tests pass in debug and release (11 ignored per profile),
including the three new controls. Model comparisons cover widths 1..16, source
offsets, both branches and every budget. A reordered predecessor forces a split;
untouched result bytes retain a visible sentinel. Four native emission variants
include the private Call ABI, profiled/unprofiled execution and high-lane slices.

The initial fixture rejection is retained separately. This experiment starts
from adopted df4006e0 and adds only scalar byte-phi coalescing; it does not carry
the parked read-only/store code. Closure verifies 231 inputs and four logs.
No project timing has run. Qualify a fresh immutable build, strict checks and
original profiles before the changed-source primary; main runtime is unchanged.
