# Bounded lossless proof snapshots

This helper retains complete proof files when their uncompressed copies would
exceed an experiment's evidence budget. It does not change benchmark inputs,
compiler checks, or application artifacts.

`measure(records, limits, capacity_guard)` reads every selected source, validates
its frozen identity and SHA-256, and computes deterministic gzip sizes without
writing snapshots. `write_verified(records, destination, projection, limits,
capacity_guard)` repeats that measurement before creating a fresh destination,
writes each unique payload, and verifies compressed bytes plus the full
decompressed contents and gzip trailer. Every logical source is checked even
when identical contents share a compressed payload. Failures preserve partial
output and reject an automatic retry into the same destination.

Callers supply explicit file, logical-byte, compressed-byte, and manifest limits.
They must bind the selected sources and projection to their launch, account for
rounded physical storage and the remaining stage evidence, and enforce their
ordinary admission lock and capacity policy. The helper launches no processes.

Seven fixture controls passed once and were independently audited. See
`results/bounded-proof-snapshot-controls-01` for exact tested sources, raw
results, and the audit. These controls establish retention behavior; they are
not compiler qualification or performance measurements.
