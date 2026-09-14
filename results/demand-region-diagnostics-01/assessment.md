# Interleaved demand diagnostics qualify

All 373 bytecode tests pass in debug and release (13 ignored per profile).
The final demand code map reconstructs interleaved fragments, checked branch
patches, assertion identities and resume entries. New controls cover six
corrupted receipts, mixed eager fallback, empty/limited arenas and live dumps
with unchanged original-PC profiles in eight configurations.

Both adopted eager captures still match exactly: 11,313,812 and 13,757,056 bytes.
Source f67c845cab3c998f432e6665e7a15cc751371f0e ran four correctness commands in
69.73 seconds. The closure binds sources, saved captures, raw logs and terminal
status. No original-project performance measurement ran.

Demand operation maps use schema 3 with per-fragment region_pc; demand range
maps use schema 2. Both explicitly mark demand_regions. Existing eager formats
remain unchanged. Next expose the option through the VM/launcher, build an
immutable candidate with full workspace/Python controls, then qualify strict
checking and original-project profiles before changed-source timing.
