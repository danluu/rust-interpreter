# Retained-exporter cost attribution

The scalar screen saved 170ms in token execution but added 144ms in Cargo and
failed its 8% complete-command target. Profile the retained compiler before
choosing another change. Source is normal Rust code on `experiment/export-costs`.

`RUST_INTERP_EXPORT_TIMINGS=1` emits two sets of exclusive wall intervals:
outer emit (lower graph, validation, serialization, hashing, publication) and
inner lower (reachable MIR/local passes, graph assembly, aggregate relocation,
call optimization and CFG). The inner intervals are nested inside lower_graph;
never add the two scopes. The disabled mode preserves existing diagnostics.
The flag affects measurement only, not bytecode or checking policy.

Build/test the exporter using the completed, disposable maintenance host cache;
its source and logs remain preserved. Compose the observer with the exact
retained VM and wrapper. Run the original token assertions across its cold
anchor, wrong production edit and five real edits in one fresh metadata cache.
Compare each artifact hash against the retained compiler's corresponding saved
first-cycle snapshot; retain and investigate any discrepancy rather than
assuming determinism. Run a focused on/off/retained artifact equivalence probe
before using the timers. No native speedup claim follows from this diagnostic.

All task activity uses the shared nonblocking benchmark lock. Preserve source
restoration and wait every child before restoring it. Maintain the 8 GiB running
floor. Keep raw command/log detail local; commit the concise cost assessment and
next decision. No additional archival batch is required.

Choose the next implementation from substantial measured exclusive costs. A
prospective candidate must justify an 8% primary screen opportunity; small
publication/hash fixes may be maintenance but do not warrant full primaries.
