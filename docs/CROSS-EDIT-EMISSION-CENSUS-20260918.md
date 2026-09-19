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

The closed typed-difference follow-up passes11controls/profile. On the valid
transition into edit1,2,648 functions change only immediate values; into edit5,
2,769 do. Data and static bytes also change. Edit4 changes names at682 numeric
function IDs and includes2,395 positional direct-call-ID changes. Immediate-only
is a syntactic classification: it does not prove a pointer relocation. Edits2/3
each change one function while all compared global fields remain identical.
[Typed differences](../results/cross-edit-emission-differences-01/summary.json).

Next compare each state against the original artifact and join actual original
per-function preparation observations by exact artifact/function metadata. This
will describe how much observed preparation is associated with unchanged bodies
and layouts, excluding no-entry functions from native-template potential. It
will not predict elapsed savings, authorize reuse or rerun the original guests.
