# Census constant direct-call arguments before specialization

Lifetime allocation reduced virtual storage substantially but regressed the
complete edited-source token command by 4.64% wall and 4.70% CPU. Keep it parked.
Investigate whether frequently executed direct calls receive constant argument
bytes, allowing a future bounded specialization to simplify code while retaining
strict Rust checking, the existing call ABI and all required runtime checks.
This is neither a larger inlining threshold nor a project-specific intrinsic.

First implement an offline typed diagnostic only. Call operands are addresses;
read argument bytes according to the callee's argument slots. Track constants
within a basic block, resetting facts at every possible branch entry and after
terminators. Do not infer initial zeroes or propagate across joins. Track exact
Local addresses and scalar immediates, constant integer arithmetic/casts/selects,
loads from immutable data or known local bytes, and stores/copies of at most 16
bytes. Do not infer mutable pointees from constant pointer bits. Unknown memory
writes and calls invalidate local memory facts. Account for partial overlaps,
aliased register outputs and faults without executing or rewriting guest code.

Bound each analyzed function to 65,536 operations and registers, at most 262,144
operands/branch edges, and 256 tracked local bytes. Use epoch resets to avoid
quadratic register clearing. Reject reports above 131,072 direct call sites and
32 MiB serialized output. Inputs are regular files bounded at 64 MiB bytecode and
256 MiB profile. Report all declined functions and their call counts.

Qualify typed fixtures for immutable/local arguments, partial overlap, calls and
unknown writes, branches/backedges, output aliasing and analysis limits. Match
profiles by function index and full operations/shape, not rendered name alone.
Use the current retained token block/exhaustive, folded and pgrust profiles;
validate original profile totals and bind every immutable input and diagnostic
binary by digest. Report executed direct calls and the fraction with constants,
argument positions/widths/values, and static site counts. These are coverage
measurements, not predicted time saved or proof that specialization is valid.

Only useful hot-call coverage justifies a separate specialization proof and
prototype. Keep original functions for unproven/indirect calls, bound code growth,
and preserve errors and argument-copy semantics. Any eventual candidate gets a
predeclared complete changed-source token screen with native/check controls,
a 10% paired wall improvement requirement and no CPU regression. Only a passing
screen proceeds to folded/pgrust guards and broader project qualification.

Use the shared lock with a 45-second wait, two build workers and an 8 GiB free
floor before workload children. Preserve sources, private data, raw evidence,
installed binaries and unrelated processes. No guest fallback to other engines.
