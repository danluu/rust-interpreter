# Corrected demand candidate qualifies as a production build

Immutable tool e5ddb4243a90 / VM b1fd894de0fe passes 637 workspace tests in both
debug and release (15 ignored each), 408 Python tests (22 skips), a release VM
build and both exact adopted eager-code reconstructions. Six setup commands took
138.80 seconds. Source a4892ff34f368e3972921856a6eea11103f5f287 uses the exact
adopted exporter and wrapper. The closure verifies 519 source/input bindings and
20 artifacts. No original-project performance command ran.

Every production register-liveness query now uses the compact representation;
the old graph is a test oracle. Sparse nonzero words or a dense bitmap preserve
all live-in queries, and explicit exceptional successors plus implicit
fallthrough preserve live-out queries. Independent seeded path tests and the
original eager words agree. The three-pair-only storage estimates are superseded
and a complete retained-storage census is next.

The explicit CLI option is --jit-demand-regions with resumable JIT execution.
Full validation is required. Preparation statistics count cumulative region
publications/refusals, eager fallbacks and retained plan/metadata payload for
each owner; they are not RSS or timing savings. Runtime adoption still requires
strict/cache fixtures, original-project profiles and changed-source comparisons.

A copied report literal originally said 407 Python passes. The raw log says
430 tests with 22 skips, hence 408 passes. reporting-correction.json binds the
correction, raw log and preserved original summary/closure; no command was rerun
and no code or artifact changed.
