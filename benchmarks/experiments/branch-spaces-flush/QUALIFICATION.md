# Qualification before changed-source measurement

Require532 workspace tests per debug/release profile (419 bytecode,113 exporter)
and10 ignored offline diagnostics. The seven new tests cover unsigned selection,
actual instruction encoding, live inputs, scalar bytes/faults/address truncation,
complete copy ranges and successor-live values across branches/joins/call modes.
All tests use the composed production candidate by default.

Reconstruct both saved adopted captures exactly. Separately stage selector-only
and composed emission, preserve full operation/region/assertion identities and
prove the composition removes exactly the successor-dead flush spans. Selector
size changes must be confined to memory operations, range guards and native
transitions. This is static accounting, not a performance measurement.

Build a fresh tool with the unchanged35df4077 compiler and wrapper, qualify the
119 strict/cache commands and three exact entropy-bound original test profiles,
then the12-test primary harness and40 fresh changed-source commands. Full held-
outs remain unstarted unless the primary passes. Passing the screen alone does
not adopt; all five full comparison gates and114 parser controls are required.
