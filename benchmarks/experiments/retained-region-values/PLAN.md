# Retain complete values inside ordinary native regions

Start from adopted main `79e72ce0`. The prior exact-origin census retains 86/40
load-payload samples; all lifetimes fit fifteen hypothetical slots. Keep every
original guest memory write. Preserve byte origins through complete local copies,
clear unknown writes, and invalidate exact known destinations of unknown-source
copies. Non-writing operations may retain captured values: their faults still
exit before any later reuse, with the same already-published frame contents.

First qualify a test-only model. Track complete scalar origins, copies, aliased
register outputs and extents with at most 1,024 operations/origins and 16,384
byte cells per native region plus an explicit charged work budget. Only 4/8/16
byte exact origins qualify. Bound live captures to fifteen slots. Require a
positive conservative static instruction credit after capture: normal reuse gets
one word; a sixteen-byte Copy gets three if lowered to a direct vector store;
captures cost one/two words. These are selection heuristics, not timing claims.

Compare concrete capture values to original Memory operations under arbitrary
initial register/frame bytes, overlap, unknown aliasing reads/writes, partial
copies, register aliases, faults and every instruction-budget prefix. Verify all
frame bytes, register values and exact errors. No executable code is published
by the model. Unknown writer/ABI effects stay barriers.

Only after this passes, audit v17–v31 preservation and integrate direct AArch64
capture/reuse emission with compile-time refusal when an original producer does
not materialize a value. Preserve original memory checks, guest register facts,
scratch-value invalidation, budgets, profiles and all writes. Capture cost and
static benefit remain unproven until emitted-body observation and the fixed
changed-source primary. Full workspace/strict/original-test profiles precede
that primary; a failed gate parks the candidate without a larger history.

Use the shared build lock, exact child receipts, two Cargo/test workers,
conservative build admission and the 8 GiB child disk floor. Preserve the paused
goal and independent compiler workstream. No other backend or workload edits.
