# Isolated whole-call candidate qualification

All 300 workspace tests pass in debug and release, with one ignored in each.
Eleven focused tests cover bounded CFG initialization (including 38,416 independent
graph-oracle cases), graph cycles/unknown callees/bounds, CompareBytes relocation,
nested calls with ordered overlapping arguments and aliased results, cross-block
values, faults, profiles, exact budgets and forced interpreter fallback.

The runtime and exporter are rebuilt from isolated integrated source plus the
tracked recipe. The rebuilt wrapper is byte-identical to control. Root Rust source
and ordinary launcher remain at qualified tool 9637b0ac. No real-workload timing
or compatibility claim yet; next are original-artifact runtime smoke, fresh real
exports, strict frontend/differential checks and fixed edited-command comparisons.

The initial build failure remains preserved. Two legacy heuristic expectations
were replaced by execution checks for the newly proven cross-block forms; their
original cold/assertion/alias/budget checks remain. A new test now handles the
retained generic native memory diagnostic while checking the exact fault budget.
No runtime diagnostics or benchmark assertions were changed.
