# Binding setup dominates this diagnostic

All16 disabled/enabled commands pass the current12-test token history:
original, wrong, five valid edits and restoration. Both modes match every
retained bytecode artifact, catalog and expected assertion outcome. The
observer's counts and timing residual reconcile; sources and frozen inputs
are unchanged after restoration. The exporter passes75 tests per profile,
five diagnostic harness checks and26 real Cargo fixture commands, including
strict uncalled errors and option-dependent invalidation.

Across the five valid edits, diagnostic medians are:

| Binding work | Time |
| --- | ---: |
| Setup: current MIR plus immediate index |100.70ms|
| Event resolution and graph/allocation effects |29.17ms|
| Call and frame-observation patching |1.18ms|
| Unassigned destruction/bookkeeping |0.77ms|
| Enclosing binding interval |131.83ms|

Independent medians need not sum exactly. This is instrumented attribution,
not a new performance comparison with the previously measured124ms binding.
The median reused5218 functions contain1,051,584 bytecode operations and
173,756 immediate sites, while replaying25,101 events and15,081 call sites.

The assumption that current-session event resolution dominates is not supported
by these intervals. Setup includes both the rustc instance-MIR query and a full
scan/index of immediate instructions, so this result cannot choose between
lazy MIR access and a stored positions table. Refine only that interval into
current-context preparation and immediate indexing before changing semantics
or storage format. The separate generated-code samples still identify guest
execution as the larger token opportunity.

[Exact observations](summary.json), [edited medians](edited-diagnostic.json),
[diagnostic plan](../../benchmarks/experiments/replay-costs/PLAN.md).
