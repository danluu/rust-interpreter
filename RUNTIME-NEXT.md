# Next work

The retained custom JIT still loses substantially to the specified native control
on the exhaustive token workflow. Repeated actual edits confirm this gap.
[Current evidence](STATUS.md), [review decisions](docs/SUGGESTIONS-REVIEW-20260910.md).

1. **Profile the native Call implementation and change the remaining costly path.**
   Ordinary Call stubs now link with generated regions. Source `26833c3` / tool
   `2f31c6a0` passes 231 debug/release tests. Three real-edit cycles improve token
   19.3% paired but regress folded 1.4%; both original gates fail. Keep the options
   experimental. Fresh profiles and same-process generated-code attribution identify substantial
   register-array stores and frame clearing. Next implement full-CFG liveness and
   persistent full-width register pairs across native edges, with complete ABI
   preservation. Keep frame lifetime/layout changes separate.
   [Implementation plan](benchmarks/experiments/bounded-native-calls/VALUE-LIFETIMES-NEXT.md). Keep the original
   b2aa6efe gates, then require held-out and broader qualification before retention.
   [Result](results/native-region-e2e-01/assessment.md),
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
