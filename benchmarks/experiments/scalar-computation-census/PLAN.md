# Saved scalar computation census

The dead-register primary passed correctness but failed its unchanged noise
gate (wall ratio 0.949959, A/A envelope 0.060657). Do not repeat that candidate.
Before another runtime change, count constant scalar computations, constant
branch/assert conditions and paired arithmetic value/overflow calculations in
its saved real hot leaves. Categories overlap and are not additive.

A test-only observer rebuilds the original scalar plans from pinned public
artifacts and exactly reconstructs every saved native scalar body in all three
profiles. Propagate only complete constants through the bounded acyclic value
graph. Constant arithmetic uses this interpreter's existing semantics; division
errors stay unknown. A focused control covers faults, overflow, casts and byte
joins. No guest body runs and no executable guest code is published.

Weight original PCs with the already-qualified successful scalar profile counts.
These are computation opportunities, not measured hardware instructions, removed
work or predicted speedups. Failed private attempts are excluded. Keep original
program, profile and native-code hashes, source bindings and command logs.

Use the existing shared target from the same source root, two Cargo workers,
benchmark lock and the unchanged build admission: max(14 GiB, 8 GiB plus twice
allocated target bytes), with 8 GiB before each child. Never clean the shared
target or any other workstream. The observer is test-only; no production runtime
or frontend behavior changes in this experiment.
