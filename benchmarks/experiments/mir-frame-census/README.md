# MIR frame inventory

The preceding typed census found large repeated frame clearing but little scope
for skipping only argument-slot zeroing. This diagnostic inventories MIR local
storage after the existing coloring and scalar promotion passes. It separates
semantic MIR uses, ABI storage, shared colored ranges and emitted local
addresses. Unnamed or unreferenced storage is an observation, not a proof that
relocation or omission preserves behavior.

`observe.rs` is injected only into a copied exporter. The production source and
retained VM remain unchanged. Qualification requires all existing exporter tests,
the exact retained VM binary, and fresh folded/token bytecode identical to the
retained artifacts, with the original tests still passing. Instrumented frontend
times are not benchmark results. No function-name or project special case is
used by the observer.

Do not reimplement the existing scalar coloring or inline scratch-bank reuse.
Use the inventory to choose a bounded candidate, then measure actual production
edits before broader qualification. All original failed attempts and regressions
remain part of the record.
