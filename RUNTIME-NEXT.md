# Next work

The retained custom JIT still loses substantially to the specified native control
on the exhaustive token workflow. Repeated actual edits confirm this gap.
[Current evidence](STATUS.md), [review decisions](docs/SUGGESTIONS-REVIEW-20260910.md).

1. **Profile the resumable native-call tradeoff.** Runtime `5574d10`, integration
   `e1bec3e`, tool `035ef708` passes all 256 debug/release tests, 12 CLI checks
   and both original artifacts. Its completed three-cycle E2E run improves
   folded 10.6% paired and token 15.0%, with CPU improving. Only folded passes;
   the combined gate fails. Native remains faster on both. Qualify profile flag
   and exact-code attribution, then capture this tool on both originals before
   selecting the next implementation. Preserve the −20% token/−10% folded gates,
   all seven held-out workflows and broader native/TLS/fre qualification before
   retention. [Result](results/resumable-e2e-01/assessment.md),
   [plan](benchmarks/experiments/resumable-native-calls/PLAN.md).
   The private-array census is parked: 0.0000073% folded and 0.1233% token scope.
   The previous tree/stub experiment (`e89de7f8`) improved token 23.6% and folded
   4.2%; its combined gate also failed. Cross-run differences do not isolate the
   cause. Required initialization still costs work when native Calls perform it.
2. **Finish native configuration qualification.** Nine workflows now have three
   real-edit cycles, child CPU, explicit root O0/incremental native settings,
   18 native build jobs, default test concurrency and independent checks.
   All 756 commands completed. Linker/backend/compiler-worker alternatives remain
   unqualified. [Assessment](results/native-controls-corpus-01/assessment.md).
3. **Resolve artifact-history differences.** Repeated source cycles changed
   readonly data layout and embedded immediate values. Paired engines agree;
   cross-history determinism is unresolved. Trace constant identities and
   relocations before introducing a function-level cache or normalizing bytes.
4. **Broaden useful execution.** Add real interface/test/dependency edits and an
   unfiltered suite attempt, recording unsupported bodies explicitly. A shared
   test graph and entry descriptors may improve selection reuse; eager export
   of all bodies is not assumed to be cheaper.
5. **Revisit durable reuse.** Cache identities need compiler/target/configuration,
   layouts, stable instance IDs, semantic dependencies and relocations. Keep
   guest state fresh across runs. Measure lookup, validation and loading costs.

Before each runtime experiment, record correctness gates, target workloads and a
meaningful complete-command performance criterion. Retain all regressions and
failed qualifications. A few milliseconds on five different edits do not justify
a broad speedup claim. Small opcode tweaks are no longer the default direction.

Native tiering is a possible explicit hybrid experiment, subject to the user's
custom-backend requirement. Its policy must account for missing/stale runtime
history, whole-target native compilation and duplicate work. It cannot promise
to match native on every command. Full panic unwinding and synchronization must
preserve Rust semantics; do not implement success-returning shims or skip cleanup.

Use only owned pinned checkouts; preserve assertions and source restoration.
Serialize task measurements under the benchmark lock. Never stop unrelated host
work to improve benchmark conditions. Clean only identified completed compiler
caches after ownership/live-file/artifact checks; preserve historical evidence.

[Earlier runtime plans and rejected experiments](docs/history/RUNTIME-NEXT-20260910-before-review.md)
