# Lightweight compiler wrapper: release qualification

Source `b54dc6e` installs tool `c341296c`. All 268 workspace tests pass in debug
and release, with one ignored. Eleven new routing tests cover package/crate/
manifest selection, test and custom-harness forms, sysroot conflicts, host
contexts and ordered MIR-flag handling. Frozen sources and installed binary
hashes verify, and the Git source index reconstructs this exact tool key.

The VM hash is identical to `78e60cdd`:
`60b00d7de39977e6512e8335d449e5eac84c48ff95819dc2feae6ed8220a859c`.
This change moves Cargo routing into a shared std-only module and adds an exec
wrapper. It changes neither guest execution nor frontend checking policy.
New manifests contain three verified executables; legacy pairs remain accepted.

The separate [process checks](../lightweight-wrapper-processes-01/summary.json)
complete fifteen commands: fourteen actual wrapper probes and one dylib query,
plus five manifest checks. The wrapper links only libSystem on this host.
Fake compiler endpoints verify exec PID/parent identity, arguments, cwd,
environment, both jobserver pipe descriptors, nonzero exits and routing errors.
They supplement the real [launcher qualification](../lightweight-wrapper-launcher-01/summary.json):
99 original checks with all 27 Python assertion ASTs unchanged, 72 successful
commands traced through the new wrapper, and an additional successful historical
two-binary tool execution. The suite includes std-MIR build scripts/proc macros,
custom harnesses, source/dependency/feature/flag/selection changes and reverts,
wrong edits and missing-sidecar refusal.

These are correctness checks. The new pipeline still needs repeated real-project
warm and cold comparisons before retention. Native-call gates stay separate and
failed; their runtime options remain disabled in the pipeline comparison.

[Release commands, source archive and exact binary hashes](summary.json)
