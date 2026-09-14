# Production build exposes incomplete liveness compaction

The first full workspace Cargo command failed before tests or guest execution.
Four production references in scratch-cache eviction and final fact spilling
still require arbitrary-register live-in/live-out queries. The earlier compact
representation retained only three persistent-pair masks; cfg(test) retained
the original graph and masked the missing production fields. This is a source
qualification failure, not a performance result.

Source db73fa95frozen in the plan never produced an installed candidate. The
closed receipt retains the compiler diagnostics and verifies 513 source/input
bindings and two raw artifacts. Earlier exact code reconstruction remains a
valid test-layout result, but its claimed compact production storage was
incomplete: the 7.7/9.7 MB captured-function estimates omit required scratch
liveness. They must not be used as admission or performance evidence.

Fix the representation to answer every register query using dense or sparse
nonzero words and implicit fallthrough successors, with explicit exceptional
successor lists. Route production and tests through these queries; retain the
old graph only as a test oracle. Re-run the full workspace, Python suite,
production VM build, exact code captures and a corrected storage inventory.
