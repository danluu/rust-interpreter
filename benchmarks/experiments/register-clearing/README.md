# Separate the two initialization costs

`run.py` builds a host-only typed artifact reader, then reanalyzes the six
already captured current-runtime processes. It compiles the actual retained
register proof. Each native Call is joined to its typed callee and checked for
exactly one guest-memory clear and, where required, a second register-array
clear. The complete short/large loop and callee sizes must agree. All prior
process, hash, range, option and sample-count checks are rerun. No guest
execution or compiler/runtime transformation is part of this diagnostic.

The [result](../../../results/register-clearing-attribution-01/assessment.md)
accounts for all 942 folded and 879 token clearing samples as guest memory;
register-array clearing has zero sampled hits. Twenty positive cases and 140
invalid identity/sequence cases pass. Only two folded functions and four token
functions need register clearing under the current proof. A stronger full-CFG
register proof is therefore parked as a performance project.

The hottest folded callee has an 18,224-byte frame and 437 clearing samples.
The existing, hash-verified MIR inventory for this byte-identical artifact
places 16,704 bytes in its local extent, predominantly aggregate layouts.
Temporary reuse alone does not address most of this frame. Existing primitive
coloring, argument-only zero omission and private-array reuse are not new
opportunities. Broader aggregate lifetime analysis must preserve padding,
partial writes, alias observations and Call outcomes.

Before adding that analysis, compare the existing enlarged MIR inlining
budgets against ordinary budgets with the current cheap native Call ABI.
Inlining was selected under a much more expensive call path. This can change
frame size, code size, frontend cost and instruction count simultaneously;
only a fresh, matched source-edit/build/test comparison can decide whether it
helps. Keep both resulting artifacts and original native/assertion controls.
