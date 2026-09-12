# Keep dispatch state for the active interpreter frame

Fixed before source edits/builds/timing. Parent04999a2 has the qualified a1f8922
Rust sources. Baseline remains the frozen deferred-binary-vm. The unchecked-register
experiment b04bbcb is parked; this candidate uses the original checked accesses.

Change only interpreter dispatch structure: hoist the current immutable Function
and checked exact register slice around a same-frame inner loop containing the
single existing opcode match. Hold the actual Frame and preserve PC writes. Exit
on Call/CallIndirect, Return, ResetThreadLocals, and each JIT fallback. No raw
pointers, unchecked indexing, copied frame, duplicated dispatch, new opcode,
proof changes, bytecode format changes or guest-specific cases are introduced.

Preserve per-op budgets/profiling, transition/error ordering, caller argument
proof indices and JIT's one fallback after native entry. Validation and all
memory/register/frame checks remain. Source and tests receive independent review.
Run workspace debug/release correctness tests and compare observed op profiles
on a bounded mixed branch/call fixture; retain existing transition/limit tests.

Performance gate uses six alternating pairs after one warmup pair against the
same six frozen public screen cases. Require pgrust OR Ruff interpreter median
paired wall improvement >=10%; neither compute case may regress >5% wall or CPU.
JIT must have no regression exceeding both5% paired median and5ms absolute median
wall/CPU difference. If the screen passes, run the five preselected confirmation
cases with that same material-regression guard for both engines, plus the ten
fixed native-oracle signed/unsigned division fixtures as correctness coverage.
All commands must preserve stdout, instructions and peak guest memory, and all
frozen inputs must remain unchanged. Only saved-bytecode runtime including VM
startup is qualified; whole edit/build/test and unknown holdouts remain unmeasured.

Preserve original failures/gates; no unchanged failed screen is repeated just
to cross a threshold. All workloads serialize on the shared benchmark lock;
no unrelated processes/caches/worktrees are controlled.
