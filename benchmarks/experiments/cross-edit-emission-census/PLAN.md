# Cross-edit structural overlap before any persistent native-code cache

The bounded emitter-workspace candidate failed the complete parser latency
gate despite smaller saved compilation intervals. It is parked. Same-process
template sharing also failed. Investigate a distinct possibility: retain useful
ordinary emission across processes and checked edits. No cache is enabled here.

First qualify a test-only structural census on adopted Rust sources. Compare
complete serialized functions at the same numeric ID, then require unchanged
direct callees, then propagate differences through the entire direct call graph.
The graph count excludes unknown indirect targets and handles cycles iteratively.
Keep global metadata, initializer bytes and the whole-program heap-use mode as a
separate equality condition. No function-name matching or skipped validation.

Seven controls cover body/layout changes, transitive invalidation, cycles,
duplicate names and shifted identities, global and heap-mode changes, partial or
invalid artifacts, indirect calls and long chains. Debug and release run with
two Cargo/test workers in the existing root build target. Exclude the explicit
ignored saved-artifact observer from this model stage. Preserve completed runs.

After model closure, read the eight original/wrong/five-edited/restored artifacts
from the closed32-command parser primary and verify all bound hashes. Report
all seven consecutive comparisons; only five valid edits are development cases.
This stage has no guest execution, JIT construction or executable publication.
The wrong artifact is fully checked but fails the original semantic assertions.
It is an invalid-result control, not a type-checking bypass.

Counts cover every artifact function, including cold code. They are not native
cache hits, emitted bytes, time savings or a sufficient cache key. A real cache
would still need exact VM/emitter/target/options identities, scalar admission and
budget state, assertion rebinding, relocations, bounded storage, corruption and
concurrency handling, and normal code publication checks. Strict frontend checks
remain mandatory before execution. Cache overhead belongs in future real-edit
end-to-end timing, including misses and cold setup.

Serialize substantial work on the root lock with45-second admission. Build floor
is max(14GiB,8GiB+2*allocated target); saved analysis12GiB and closures8GiB. Preserve
peer work and the paused goal. No new performance campaign is admitted by this
plan, and no earlier failed candidate is rerun.
