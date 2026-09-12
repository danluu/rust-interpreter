# Call-path audit before the next implementation

The combined engine's immutable build03 remains the measurement candidate.
Choose the next implementation from its complete-command and stage results.
This is a source audit, not another runtime screen or a speed prediction.

`Assembler::reg_address` in `crates/bytecode/src/jit.rs` uses x16 once a
virtual-register offset no longer fits the scaled12-bit load/store immediate.
Both `get` and `raw_spill` reach it. Resumable calls spill persistent pairs,
read argument registers, and read the return destination after initially
loading the callee target into x16. Removing the second `callee_target` load
alone is therefore incorrect for large register arrays. A future change must
give these call-local accesses a proved nonconflicting scratch register or
retain the reload. Do not change the general scratch register globally:
ordinary emitters have different live operands. Include argument, result and
live persistent spills beyond the immediate-address range in execution tests.

`checked_address` uses x13/x14/x15/x17, and the ABI copy helpers use x9/x10,
x11/x12 and q0..q7. The combined budget stays in x22. Frame and register
clearing preserve x17 and x22; result-address checks can overwrite x17, which
is why the return path loads its register-base metadata after the checked
copy. Maintain that order even if more call state moves into native registers.

The call guard currently reads both FRAME_END and FRAME_LIMIT. Preparation
already caps spare frames by the logical limit, and Boundary validates the
active and prepared extents before native entry. A future effective bound can
merge those two checks explicitly. The memory extent, register extent and
combined working-memory budget are separate constraints. One scalar slack
check needs a new proof covering all three deltas, alignment and overflow;
replacing their comparisons with an unproved minimum is insufficient.

The current descriptor pointer x20 already advances by48 bytes per successful
call and retreats on return. FRAME_LEN is also updated through memory. Using
the pointer as the native depth representation could remove repeated loads
and stores, but every decline, fault, interpreted boundary and budget exit
must publish the correct integer depth. A fault during argument copying must
still leave the old active frame. Descriptors cannot be elided merely because
a function has no Calls: assertions, bounds faults and budget exhaustion also
exit native execution.

CALLS and RETURNS are adjacent64-bit counters. They currently cost a
load/add/store for each successful transition. Vector registers above q7 are
not named by the current emitters; investigate accumulating transition counts
there as part of the same call rewrite, with an explicit register-clobber
contract and publication at every native exit. Availability in this source
audit is not an ABI or correctness proof. Keep exact profiler counts, tiny
instruction budgets, TLS callbacks and failed-copy behavior in qualification.

ABI copies above128 bytes currently use directional byte loops. Wider chunks
are valid only when load-before-store ordering handles overlapping ranges,
including a one-byte source/destination displacement. Preserve exact tails
and source-check ordering. This belongs with the call-transfer work, not a
separate threshold-chasing microbenchmark campaign.

The old tree/stub paths still share `abi_copy` and zero helpers. Audit their
public switches and qualification users before retiring them; removal and
the call rewrite must have explicit compatibility scope. Main's reference
interpreter remains necessary for differential execution.

Local Xcode exposes a CPU Counters template. This establishes tool discovery
only, not permission or availability of retired-instruction events. A later
bounded probe must launch only an owned process and verify actual event data
before comparing equal native/JIT scopes. Sampling PCs cannot substitute for
retired instructions, and unrelated processes must remain untouched.
