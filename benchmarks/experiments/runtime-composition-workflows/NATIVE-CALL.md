# Strict workflows and exact profiles for the new runtime composition

Use immutable tool45a1529e, built from2599a193 with666 Rust tests per profile,
25 ignored, and436 Python tests (414 passed,22 declared skips). The VM combines
native indirect transitions, checked readonly scalar leaves and successor-only
spilling with the adopted scratch/scalar runtime. Compiler/exporter/wrapper are
unchanged adopted df4006e0 binaries. Component failures stay failures; no gain
is inferred by addition.

Run122 strict/cache commands with both native-call flags: native/interpreter/JIT
fixtures, original seeds, cold/warm/automatic function caches, C-string and
environment checks, genuine Cargo helper edits and unreachable type/borrow
errors. Reject actual partial-validation artifacts with indirect-only and combined
flags. Verify source restoration and all expected negative results before closure.

Qualify five operation-map controls and nine launcher controls freshly. Then run
three original candidate profiles (block, exhaustive, folded) against three retained
adopted profiles. Require exact logical counts at every original PC, instruction
and peak-memory counts, entropy consumption, and complete emitted-code ownership.
Entropy replay is used only for these identity diagnostics, never timing.

Use the shared lock,12GiB admission,8GiB child floor and two-worker limits.
After all qualifications pass, run the fresh40-command full-token primary with
all12 original tests and the unchanged gates in SCREEN.md. Main remains adopted
unless the primary, prospective five-project histories and both parser guards pass.
