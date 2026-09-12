# Profile selected real tests without rewriting saved artifacts

The expanded token module has two expensive tests: the newly included block
boundary test and the exhaustive test already present in the old subset. Prior
samples of the three-test artifact do not cover the expanded suite. Both attempts
to increase register capacity have now been rejected; measure representative
current execution before choosing another emitter change.

Add VM `--profile-test EXACT_NAME`, requiring `--profile` and the existing
artifact-bound `--suite-catalog`. Validate the complete catalog against the original
bytecode and accept exactly one zero-argument/unit-result entry. Change only the
in-memory entry, emit selection provenance, preserve every function and the saved
file, and start fresh guest/JIT state. Reject missing/stale catalogs, unknown names,
entry arguments, isolated-batch combinations and existing output files. Leave
normal suite execution and the profile schema intact. This is a diagnostic path,
not prepared-suite timing or a change to frontend checking.

Qualify with a fixture whose root and unselected test trap, both interpreter and
JIT profiles, exact counter reconstruction, unchanged input bytes and rejection
controls. Then profile current restored token block-boundary and exhaustive tests,
the dominant folded test and representative pgrust tests. Bind original artifacts,
catalogs, exact names, VM and source, command receipts, logical counts and profiles.
Use recorded entropy where comparing executions, with no interposition in Cargo.

Attribute executed operations, native blocks, calls/returns, block lengths and hot
functions. If investigating CFG transformations, use typed bytecode for operands
and edges; Debug labels are only for descriptive operation grouping. Instrumented
counts are not machine-time attribution. Sampling can resolve a specific remaining
uncertainty after counts. Choose a structural candidate from this evidence and
screen it before spending time on full edited compilation histories.

Serialize workloads with the global lock, a 45-second wait and 8 GiB disk floor;
two workers for host builds. Do not modify saved bytecode, previous raw profiles,
private data or unrelated workloads. Qualified changes go to main; failed cache
experiments remain on their separate branches.
