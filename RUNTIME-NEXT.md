# Next work

The retained custom JIT still loses substantially to the specified native control
on the exhaustive token workflow. Repeated actual edits confirm this gap.
[Current evidence](STATUS.md), [review decisions](docs/SUGGESTIONS-REVIEW-20260910.md).

1. **Measure additional safe frame reuse before changing layout.**
   Full-width register values now persist across native branches and calls.
   `d664bce` / `e89de7f8` passes 240 debug/release tests. Three real-edit cycles
   improve token 23.6% paired and folded 4.2%. Token passes its original gate;
   folded misses 10%, so the options stay experimental. Fresh exact-code
   profiles put folded VM frame reservation at 24.9% and generated zeroing at
   9.0%; direct register-array stores are 3.6%. These shares are not savings.
   Next inventory additional fully overwritten private aggregate ranges with
   noninterfering lifetimes, preserving padding, aliases and entry zero values.
   Keep existing scalar coloring, unused-local and argument-zeroing work separate.
   [Bounded diagnostic plan](benchmarks/experiments/aggregate-reuse-census/PLAN.md).
   Keep the original b2aa6efe gates, then require held-out and broader qualification.
   [Result](results/persistent-e2e-01/assessment.md),
   [profiling protocol](benchmarks/experiments/bounded-native-calls/PROFILING.md).
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
