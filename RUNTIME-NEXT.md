# Next work

The retained custom JIT still loses substantially to the specified native control
on the exhaustive token workflow. Repeated actual edits confirm this gap.
[Current evidence](STATUS.md), [review decisions](docs/SUGGESTIONS-REVIEW-20260910.md).

1. **Link native Calls with ordinary JIT regions.** The bounded-tree path is
   implemented and passes 225 debug/release workspace tests. Its three-cycle
   real-edit result improves token 14.4% paired but regresses folded 3.0%; both
   original gates are missed. It still performs millions of outer calls through
   the VM. Keep `c98d995b` experimental and implement direct Call stubs that preserve
   readiness, budgets, storage bounds, copy semantics and fault exits. Compare
   against b2aa6efe with the same gates, then run held-out/broader qualification
   before retention. [Result](results/bounded-native-e2e-01/assessment.md),
   [implementation notes](benchmarks/experiments/bounded-native-calls/REGION-CALLS-NEXT.md).
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
