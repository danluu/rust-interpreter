# Resumable emitter implementation contract

Implemented by runtime `5574d10` and launcher/gate integration `e1bec3e`, tool
`035ef708`. All 256 workspace tests pass in debug/release, one ignored. Twelve
CLI checks and both original real artifacts pass. The original three-cycle
E2E run improves folded 10.6% and token 15.0%; only folded passes its original
gate. Exact-code profiles are next. The notes below document the selected contract;
follow-up work must preserve it and the original performance/held-out gates.

## Existing code to reuse

- `frames.rs` provides initialized descriptors, a hidden spare prefix,
  `prepare`, `prepared_mut_ptr`, `prepared_frame` and checked publication.
  `Frame` is host-only `repr(C)`: five usize fields and a bool, 48 bytes on this
  target. Use named `frames::layout` offsets and byte access for the bool; never
  read padding. Native pushes overwrite every field and set the bool false.
- `native_continuation.rs` provides `Boundary`, `Capacity`, `State`, typed
  `Status`/`Exit` and `Run`. `State` starts with remaining budget/profile pointer
  at the ordinary cursor offsets, then memory length/peak, register/frame
  lengths and successful push/pop counts. Its named layout is compile-checked.
  A future extended cursor should embed State first and append immutable
  backing pointers, prepared bounds, guest limits and trusted entry tables.
- `Boundary::finish` checks backing identities, active host extents, fixed
  heap/TLS accounting, working-memory/depth limits, budget and push/pop counts,
  and the resulting top descriptor before changing active lengths. It permits
  one-past-code for existing budget-before-invalid-PC ordering. A zero-progress
  decline must retain entry descriptor/extents/peak; positive progress at the
  same PC is a resume. A terminal fault is a separate outcome. It does not prove
  per-Call intermediate limits, zeroing, copy effects or ancestor integrity.
- Ordinary `emit_function`, liveness, `local_fills` and operation lowering are
  reusable. Keep current tree/stub code as independent differential controls.
  Share `zero_range`/`abi_copy` through narrow visibility changes when needed.

## Entry metadata and host ABI

Add an explicit experimental mode to Jit and a constant VM specialization.
Compile one ordinary body per function for this mode. Every generated block has
three positions: its external host prologue; a function-resume entry that loads
its persistent assignment; and an internal same-function entry after those
loads. Same-function links retain assigned values; cross-function transitions
use the resume entry. Include standalone Call and Return regions, each with
independent preflight/budget accounting. Consider emitting short supported
regions too: they can now be reached without a VM transition.

All external resumable entries must save the same complete x19–x28/LR set,
regardless of the entering function's allocation. A 96-byte aligned frame can
hold x19/LR, x20/x21, x22/padding, x23/x24, x25/x26 and x27/x28. Never push another
host frame for a guest Call. Keep x18/x29 untouched. Preserve ordinary x0/x1
register-array/frame bases, x2/x3 linear pointer/length, x4 read-only bound,
x7/x8 heap pointer/length, x19 cursor, and x23–x28 persistent guest values.
x20 can retain the current guest descriptor; x21/x22 can hold callee bases
across argument-copy helpers. Helpers clobber x9–x17: reload code targets after
them, never assume those scratch values survive.

Prepare a fixed outer function table and immutable per-PC resume-pointer tables.
Stage vectors/code/relocations first, publish metadata only after successful
append/protection changes, and keep all backing stable during native execution.
Targets derive only from emitted offsets in the owned code arena. Cold or
missing target entries decline the Call before progress. No guest value may
be converted to a host code pointer. Preserve typed capacity/codegen declines.

## Call, Return, and VM integration

Before native entry, prepare bounded spare frames/register slots/linear bytes
without increasing guest active extents. Preparation failure disables native
Calls for that entry; ordinary regions should remain executable. Start with
explicit conservative spare bounds, not a whole-function/recursive-tree plan.
Native guards check overflow, prepared storage and the actual guest limits at
each Call. A guard declines to VM; it must not raise a later guest error early.

The existing VM's Call order is frame reservation, register-size/working-memory
checks, argument copies, depth check, register growth/zeroing, then frame push.
Preserve it. Native preflight may prove later checks succeed, but otherwise
decline before consuming Call. On success, charge Call once, clear the exact
old-live-end through new-live-end range (including alignment padding), update
peak, copy arguments in order, initialize callee registers under the existing
proof, save caller PC+1, push a complete descriptor and establish callee state.
Spill caller assigned values live at the return PC before changing assignments.

Inner Return copies the result before truncating to the callee's aligned base,
pops the descriptor, updates register extent, restores caller state and reloads
its assignment through a trusted resume entry. The caller can predate the
current native entry. A root or TLS callback Return declines unconsumed so the
existing VM completion/destructor path runs. Unsupported operations and budget
tails spill the current function's live values, save its exact PC, and return
through the one external host frame. Terminal faults never perform later copies.

The VM must end its old top-frame borrow before entering native code and reread
the top descriptor after `Boundary::finish`. Interpret the returned operation
once, including a no-progress decline, before retrying JIT eligibility. Check
instruction exhaustion first. Do not use the outer function/PC or infer progress
from PC inequality. Switch ordinary profile-counter pointers on function
transitions and publish matching block ends for all prepared functions. Call
and Return regions count one logical operation each; profiles must reconstruct
the full logical count without interpreting native-tree counters as this mode.

Next qualify emitted execution and all ABI/budget/error/copy cases in PLAN.md,
then CLI/workflow flag verification, release installation, original-artifact
smokes and the same three-cycle b2 comparison. Keep the original −20% token and
−10% folded gates, CPU requirement and held-out/broader qualification.
