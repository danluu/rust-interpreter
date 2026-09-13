# Conditional current-frame disjointness census

The completed strict range census loses frame-slot pointer identity after a
pointee write, because that write may change the slot. Count a separate,
explicitly conditional model before deciding whether to implement a guard.
No guest execution path, checking policy, emitted instruction or timing gate
changes in this experiment.

Within each exact saved native region, the first modeled write through an entry
root may select one protected root. Later loads from frame slots can preserve
only that same root's identity, conditional on every modeled write through it
being disjoint from the entire active frame. All such writes enter the complete
group extent. Other roots, unmodeled writes and known overlapping local writes
still invalidate slot knowledge. Slot-loaded constants and unrelated roots
cannot inherit this assumption. Already captured register values retain their
identity; fresh regions reset every assumption. Strict mode remains unchanged.

Keep the existing bounded analysis, at least three accesses and at most 4 KiB
extent. Report best-group counts and the subset requiring frame disjointness
separately. These counts are neither guard hit rates nor emitted savings or
latency predictions. A future runtime implementation must validate entry data,
range arithmetic, arena/tag classification, readonly requirements and frame
disjointness. On any failed preflight, original ordered execution must preserve
faults, partial writes, budgets and progress. The census implements no guard.

Qualification requires 470 workspace Rust tests per debug/release profile, one
ignored test, including four conditional provenance tests. Snapshot only the
offline executable. Then run exactly thirteen CLI commands: three conditional
censuses of adopted hash-bound profiles; byte-identical outputs from the three
previous modes; and seven bounded-input/output-preservation rejection controls.
Zero guest commands and zero timing comparisons are added. Retain failures.

Use the shared benchmark lock with a 45-second admission, two Cargo workers,
and an 8 GiB per-command floor. Preserve peer work, the independent disk cleaner,
the paused goal and existing evidence. If useful groups expand materially,
design and qualify a generic guarded runtime candidate; otherwise park it.
