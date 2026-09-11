# Bounded native call-tree experiment

Status: the complete native call-tree path is connected behind
`--engine jit --jit-native-calls` (or `Limits.jit_native_calls`).
[225 workspace tests pass](../../../results/bounded-native-vm-03/summary.json).
The launcher forwards this runtime option without changing the MIR workspace
identity. Paired benchmarks enable it only with `--candidate-jit-native-calls`.
The optimized build also passes 225 tests. Three-cycle real edit/build/test
measurements are complete: token improves 14.4% paired, folded regresses 3.0%.
Both original performance gates are missed. [Assessment](../../../results/bounded-native-e2e-01/assessment.md).
Keep this version experimental; next implement [ordinary-region Call stubs](REGION-CALLS-NEXT.md).

The current implementation caps speculative frame span at 256 KiB, register
storage at 65,536 u128 slots and native nesting at 64 frames. These are
optimization declines, separate from guest limits; actual retained scope must be
measured when the native path runs. [Emitter integration notes](INTERNAL-ABI.md).

The [stronger native controls](../../../results/native-controls-corpus-01/assessment.md)
leave token at 6.664 s custom versus 2.002 s native and folded at 2.485 versus
1.638 s. The [typed census](../../../results/native-call-census-02/summary.json)
finds that acyclic direct-call trees with explicit terminal-Trap handling cover
80.72% of token direct calls / 59.02% of their frame bytes and 54.61% / 17.55% for folded.
Strict leaves alone cover only 15.04% and 16.93% of direct calls. Counts are not time or
predicted savings. All eligible observed calls have tree bounds below 8,192
virtual instructions; use that as the initial eligibility bound.

## Execution design

- Keep rustc's strict checking and our interpreter/emitter. Add an explicit
  experimental option, with the current engine retained for paired comparisons.
- Compute conservative whole-tree instruction, depth and storage requirements
  from typed operations. Reject CFG cycles, recursive call graphs, unsupported
  operations and arithmetic overflow. Include each static call site, Return and
  terminal Trap; repeated calls to the same target count repeatedly.
- Prepare every target and all backing storage before a bounded tree starts.
  Published code and entry metadata must remain stable during execution. Lazy
  staging or capacity decline must leave the existing VM path usable. Do not
  enter a partially prepared tree and assume its cold branches are unreachable.
- Guard the whole call's budget before progress. With insufficient budget or
  readiness, execute through the current interpreter/JIT path. A whole-tree
  instruction bound does not bound time spent in CompareBytes or memory copies.
- Separate initialized backing bytes from active guest memory bounds. Preserve
  frame zeroing, alignment, register initialization, working-memory limits,
  argument-copy order, result aliases, readonly/heap checks and error ordering.
  Return truncates to the aligned callee base, retaining preceding padding.
- Native Call/Return must preserve caller registers and invalidate memory facts
  that a callee can change through aliases. Account for executed operations and
  profiles in every called function. Preserve terminal trap messages/identity.
- A bounded tree either returns completely or terminates with the proper guest
  error. It must not silently exit partway to an outer frame. Native nesting must
  have a checked host-storage/depth bound; no unbounded host recursion.
- Leave root/TLS completion to the existing machinery. Do not claim new panic
  unwinding, OS/FFI, concurrency or libtest support from this optimization.

[Detailed ABI audit and broader alternative](../../../docs/NATIVE-CALL-EXPERIMENT.md).
If this bounded path cannot retain its measured scope under real readiness and
storage limits, revisit the general continuation ABI rather than disguising the
lost coverage or shrinking the benchmark.

## Predeclared gates

Correctness precedes performance: differential calls with aliases/overlapping
arguments, zero-sized values, frame padding, live-memory boundaries, nested depth
and working-memory limits, terminal faults, short regions, code-capacity declines,
and budget points immediately below/at/above the whole-tree bound. Verify fault
order and native ABI preservation, plus per-function profile/step accounting.

For experimental retention, target at least **20% lower median paired complete
token command latency** and **10% lower folded latency**, with child CPU improving
in the same direction. Use three balanced edit cycles and the frozen original
cases, wrong-edit controls, flags/limits, and stronger native configuration.
Report execution, export, code-generation and preparation costs separately.

Run the remaining seven workflow controls as held-out checks. An unresolved
regression above 5% blocks default retention; repeat affected real edits when
variation prevents a decision. Thresholds are engineering targets, not confidence
intervals. A failed gate retains the evidence and leaves the baseline enabled.
Any production retention also requires the broader native differential/TLS/fre
execution qualification on the final candidate. No whole-codebase adoption claim
follows from passing these selected batches.
