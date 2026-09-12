# Exact exporter capabilities published

The exact candidate exporter was probed and all four launcher export-option guards pass. The exporter hash now matches its installed executable. Capability semantics, all binaries, source and ready manifests remain unchanged; before/after receipts and probe output are verified. The isolated builder requires this explicit publication step; normal launcher publication already probes its exporter.
