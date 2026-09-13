# Native bridge prototype contract

The current census supports a prototype: 55.85% / 74.45% of native direct calls
have complete bounded plans. No performance result exists. Start from the
qualified runtime source on `experiment/resumable-tree-bridge-20260913`, retain
the current ordinary Call path, and add an explicit disabled option requiring
resumable execution. Do not combine the existing standalone native-tree flag.

Before a normal function is emitted, prepare eligible direct-call trees and
their entire cold dependency closure. Use the exact existing bounded planner,
stable MAP_JIT arena and immutable published offsets. Bound additional code;
retain the 16 MiB default. A missing plan, unsupported body, unavailable code or
capacity decline leaves the ordinary Call available. Never publish a partially
prepared tree entry. Preserve ordinary code readiness on failure.

At the bridge Call, check the entire conservative instruction bound, depth,
initialized frame/register backing and guest working-memory budget before
charging any operation or changing guest state. Include root alignment and all
sibling padding in the exact tree bound. An insufficient stronger guard branches
to the existing resumable Call, allowing its ordinary partial-budget behavior
and fault order. No inferred type or lazy borrow check participates.

After admission, charge the outer Call once, spill its live persistent values,
clear its exact new frame/padding, and validate/copy arguments in original order.
Preserve the complete current fixed/bulk clearing helpers and register-zero
proof. Result addresses remain unchecked until Return, as in the current engine.
Root argument failure still uses the original caller descriptor and accounting;
the root has not been entered yet. Do not mark a call successful before all
arguments and initial registers are ready.

Use an embedded bridge cursor whose prefix matches the existing TreeCursor.
Save the resumable cursor/caller state on a bounded host stack, switch x19 to
the tree prefix, and enter a complete native tree through a host-owned target.
x22 is a register cursor inside the old tree ABI and the remaining instruction
budget outside it; save/restore and explicit publication must reconcile them.
Keep all x19–x28 values, LR and stack alignment valid across success and errors.
Profile tree regions into their separate jit_tree_blocks arrays and publish
their exact ends. Do not treat the ordinary and tree partitions as identical.

On success, the tree has copied its result and left its aligned root base as
the live memory end. Restore the caller register/frame bases, remaining budget
and persistent values. Publish exact nested/root Call and Return counts, peaks
and a pc+1 caller continuation. Keep the frame/register active lengths unchanged
after a completed tree. Maintain separate bridge invocation/instruction counters
so backend placement can be reconciled with per-PC profiles.

Fatal errors must still pass the existing Boundary::finish validation. Do not
bypass it or manufacture balanced transition counters. Track a bounded private
tree depth and successful Call count; store each function's last successful
call continuation in its host frame. On a fault, capture the active depth and
register end once, then materialize each active descriptor into the prechecked
prepared Frames array while unwinding. Recover bases from that function's saved
entry register/frame pointers, keep the return address and function identity,
and set TLS false for these ordinary calls. Ancestor PCs reflect only completed
argument admissions. The captured fault depth determines actual completed
Returns from successful Calls. The adapter publishes the resulting valid top
frame, live memory, register extent and exact remaining budget before returning
the original fault code. Preserve the original caller descriptor throughout.

Do not silently lose current body optimizations. Two eligible captured functions
use guarded ranges, whose stronger-check failure currently returns to the VM.
A complete tree needs an internal unchanged-entry slow body for such a failure,
or an explicit general eligibility exclusion propagated through the call graph.
Select and measure that rule before runtime timing; never specialize by names.

Qualification order: arithmetic/layout and fault-materialization controls;
native ABI probes and interpreter/JIT differential fixtures over success,
overlapping arguments/results, dirty registers, unusual widths, padding, nested
faults and all limits; workspace debug/release controls; original strict/cache
and real-test profiles; then a preregistered changed-source 40-command primary.
Only a passing screen proceeds to full primary and held-out projects. Preserve
every decline/failure and setup cost, serialize under the shared lock, use two
workers and conservative disk admission, and keep the saved goal paused.
