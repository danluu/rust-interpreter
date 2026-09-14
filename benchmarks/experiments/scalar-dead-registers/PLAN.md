# Scalar dead register elimination

The saved-body census found 733–822 million dead pure-register word executions
across successful scalar Calls in the original token block test. Try that
mechanism as one runtime-only revision on the parked scalar Call composition.
The adopted VM remains the control; no existing failed screen is repeated.

Use a custom bounded AArch64 pass: decode this emitter's finite instruction set,
prove the machine CFG acyclic after exact unconditional-Trap recognition, and
propagate register liveness backward. Remove only unused pure definitions.
Preserve memory operations, SP changes, every branch, failure tail and return.
Repatch every branch before executable publication. Unknown encodings or CFGs
leave the original emitted body intact. Keep the historical unoptimized emitter
available in tests for exact archived code reconstruction.

The pass uses a constant number of linear traversals and arrays bounded by the
existing 65,536-word body limit. It runs only during host code preparation. Its
preparation cost belongs inside end-to-end benchmark timings. No LLVM, foreign
interpreter, guest callback, frontend change or weakened checking is introduced.

First qualify the dependency-free pass directly with rustc in a new isolated
directory. This compiles one std-only module and its tests, without a Cargo
graph or shared target. Reserve 10 GiB free and cap its completed output budget
at 512 MiB; require the usual 8 GiB child floor. Compare both debug and release
against all 137 saved scalar bodies and independent relocation of the qualified
dead-word sets. This is preliminary host qualification only. The existing
14 GiB minimum (or 8 GiB plus twice allocated target size) still applies to all
workspace Cargo builds; it is not lowered for this probe.

Then run the complete scalar native/Call controls in both profiles, workspace
checks, strict Cargo/cache qualification and exact original profiles. Extend the
register-pressure, cross-block and private-fault controls to the optimized
variant. Use the same 40-command edited-source token gate. Only a passing screen
permits the full project comparisons and parser compatibility work. No runtime
adoption follows from static counts, preliminary tests or a point estimate.

The saved-word probe passes in both profiles. An additional isolated std-only
probe now runs each original/optimized saved body on 128 deterministic synthetic
argument sets. It checks the complete private Output even on failure, status,
callee-saved registers and SP. All memory accesses are checked against the
qualified input/Output/stack contract before publication. This uses the existing
custom MAP_JIT publisher and the same small-probe admission. It supplements the
full VM qualification and does not substitute for real project tests or timing.
