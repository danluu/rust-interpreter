# Proposed native-call experiment

Status: design requirements, not an implemented feature or predicted speedup.
The current native-control corpus must finish before selecting its performance
gate. The latest token CPU sample attributes substantial time to dispatch,
frame preparation and argument/return handling, but these shares cannot simply
be removed or added into a speedup prediction.

## First decision: measure reachable scope

Use the typed bytecode and an exact matching execution profile to count dynamic
calls whose callees can complete using the current emitter's supported operations.
Start with direct leaf calls and classify exclusions explicitly: nested calls,
indirect calls, allocation, TLS/OS operations, short interpreted regions and
unsupported arithmetic. Reuse or extract the actual support predicate; do not
maintain an approximate second opcode list. Function display names are not unique
identities. Report call count and observed cost coverage, not just static functions.

If this subset excludes the expensive calls, do not build a small native-call
path merely because it is convenient. Reconsider the calling convention and
broader continuation design before another small performance experiment.

## Required execution contract

- Preserve argument copy order, aliases, frame alignment/initialization, return
  copies, working-memory/allocation limits and call-depth failures.
- Keep memory and register storage stable while generated code runs. Reserving
  Vec capacity alone does not initialize elements or change the guest's logical
  address bounds. Any reusable scratch storage needs explicit initialized and
  active ranges; it must not make previously inaccessible guest bytes readable.
- Keep published entries immutable and lazy generation safe on the owning
  MAP_JIT thread. A direct call target must come from trusted emitter metadata.
- Preserve exact instruction accounting and fault order. When a partially
  executed callee reaches an interpreter-only operation or budget tail, resume
  that callee with its actual registers, frame, PC and return destination. Merely
  reporting a budget error can hide an earlier memory/arithmetic fault.
- Distinguish a capacity decline before entering the callee from a continuation
  after partial callee execution. Do not charge an unexecuted Call twice or count
  zero-progress fallback as a successful native region.
- Preserve profiling identities and counts for caller and callee. Enclosing
  region counts must not claim an operation that fell back to interpretation.
- Keep ordinary guest errors explicit; native calls do not provide panic
  unwinding, general FFI, synchronization or TLS support by themselves.

The current call path in `crates/bytecode/src/lib.rs` establishes a specific
order: reserve the aligned, zeroed memory frame; check added register storage;
copy arguments in order; check depth; initialize/reuse registers; push the frame;
prepare its JIT entries. An argument-copy fault therefore precedes a depth fault.
A native preflight may decline to the interpreter before progress, but must not
raise a later guest error early. Return copies the result before truncating memory
to the **aligned callee base**, retaining any padding before that base. Restoring
the pre-call length instead would alter the present guest address bounds. These
are compatibility requirements for this experiment, not proposed new semantics.

## Qualification

Require interpreter/JIT differential checks for argument/result aliases, zero
sizes, nested stack limits, capacity exhaustion and every budget boundary around
Call/Return. Verify native ABI preservation and that declined staging leaves
previous code usable. Then run unchanged original tests through actual edits,
including the wrong-edit controls, with the stronger native configuration and
repeated source histories. Measure complete commands, execution and compiler CPU.

Register allocation across loops/calls and persistent function artifacts remain
separate design questions. First establish whether this call boundary removes a
material part of the measured gap while preserving the execution contract.

## Broader alternative if leaf scope is insufficient

Keep an explicit guest frame stack and branch between generated function entries;
do not map guest recursion onto unbounded host stack recursion. A host-only,
`repr(C)` cursor can carry active frame/register/memory lengths and continuation
state. Generated Call/Return operations would update that stack and use trusted
entry tables. Unsupported operations, unprepared code, insufficient initialized
storage and root/TLS returns would resume the existing interpreter.

This requires separating initialized backing storage from live guest memory
bounds throughout `Memory`, as the register stack already does. Reusing retained
bytes must zero exactly the range a current `reserve_frame` would initialize.
Any growth and lazy code publication occur outside generated execution; a cold
call can fall back before progress and enter the normal preparation path. Entry
tables and backing arrays need stable addresses during every native entry.

Call/Return must be explicit region boundaries. A pre-call decline consumes no
Call instruction; a completed native Call consumes it once. On a partial callee
exit, the VM reads the current top frame rather than the outer entry's frame.
The current `Jit::run` zero-progress rejection and same-function return-PC contract
therefore need typed replacement, not an unchecked exception. A generated Return
at the outer entry depth leaves VM/TLS completion to the host; an inner Return
copies the result, pops the guest frame and selects the caller's next native entry.

The emitted Call boundary must also invalidate cached guest-memory facts: a
callee can change caller memory through argument pointers. Scalar register values
need correct spills/restores across the new ABI. Existing region-local forwarding
proofs do not establish validity across a call.

Implement storage/continuation invariants and native transitions together in an
isolated experiment, with the existing engine available as the differential
reference. A storage-only refactor is not itself a performance result.
