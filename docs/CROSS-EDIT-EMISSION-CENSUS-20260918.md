# Structural overlap across checked parser edits

The first saved-artifact census shows that unchanged Rust source structure does
not imply stable bytecode function contents across edits. It does not yet justify
implementing a persistent native-code cache.

Seven model controls pass in debug and release. The offline observer validates
eight exact saved artifacts from the completed114-test parser comparison and
examines all seven consecutive transitions. It constructs no JIT, executes no
guest and publishes no native code. The original preflight failure is retained:
restoring source did not reproduce the first artifact hash, an equality the
original benchmark had never required. Per-state candidate/control artifacts
and restored source did match in that completed benchmark.

Across the five valid edits, exact same-ID function bodies cover roughly30–100%
of bytecode operations. Two edits change only one of11,832 functions; other
edits change many more serialized bodies. Requiring unchanged direct callees
reduces coverage further; requiring an unchanged transitive direct-call graph
with no unknown indirect targets covers roughly13–53% of operations. These are
all-artifact counts, including cold functions, not executed-code or time coverage.

The deliberately conservative whole-program context comparison also includes
initializer bytes, global metadata and heap-use mode. It differs on three of the
five valid edits. That does not establish which component changed or whether all
of those fields are necessary inputs to a particular emitted function. Likewise,
transitive body identity is not established as a necessary condition for ordinary
emission. A complete cache key needs an emitter dependency proof, not either
blindly weakening these filters or treating them as the definitive reuse limit.

Next classify the differing global fields and same-ID functions: metadata,
operation structure, direct-call identities and immediate values. Join useful
overlap with actual preparation coverage before selecting a runtime mechanism.
No type/borrow checks may be deferred; no persistent native cache is enabled.
The original [model and census plan](../benchmarks/experiments/cross-edit-emission-census/PLAN.md)
and [closed result](../results/cross-edit-emission-census-02/summary.json) retain
all transitions and their exact artifact identities.
