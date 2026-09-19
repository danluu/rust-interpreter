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

Preflight01 failed before any diagnostic command: it incorrectly required the
original and restored artifacts to have identical bytes. Both exact retained
artifacts passed the original closed history with matching per-state arms, but
their hashes differ. The failure is closed and preserved. Census02 requires
source restoration (the original contract) and compares the differing artifacts
without assuming cross-state byte identity. All eight states remain included.

Census02 is closed. It finds uneven body overlap and global-context differences
on three valid edits. The next test-only module separates individual global
fields and same-ID metadata, operation-count changes, immediate values, direct
call IDs, assertion messages and other positional differences. Position-by-
position categories are emitted only when operation counts match. Immediate-only
does not mean pointer relocation and never authorizes native reuse. Preserve all
seven comparisons and at most four examples per changed function. Model02 runs
the seven original controls and four additional typed-difference controls in
debug/release, excluding both explicitly ignored saved observers. Differences01
then reads the same eight exact retained artifacts with no new guest/build of the
project. All existing resource, strict-checking and publication boundaries apply.

Differences01 is closed: data/static bytes, immediate values and sometimes
function/call IDs change substantially. The next original-anchor census compares
the exact initial artifact with each retained later state, so a later saved-trace
join can bind actual original function names and operation counts. It additionally
reports a weaker necessary candidate condition: unchanged caller bytes and direct
callee frame/register/argument/result layouts. This is distinct from unchanged
callee bodies and does not prove scalar admission or emitted-code equality.
Model03 runs12controls/profile before anchors01. No new original guest capture,
benchmark or code cache is involved; overlapping diagnostic timing weights will
remain descriptive and must exclude functions with no published ordinary entries.
