# Bounded private-store scalar qualification

This candidate extends explicit scalar Calls with bounded private external stores and read forwarding,
with ordinary-call replay on private failure or uncertain partial aliases. It uses the
adopted df4006e0 compiler/launcher with a separately keyed VM. Strict type/borrow
checking and full-validation requirements are unchanged. Both later performance
arms enable scalar Calls; no foreign guest backend or entropy shim is used for
changed-source timings.

Run the existing 121-command strict/cache qualification with the candidate:
original native-oracle fixtures, reused artifacts, real partial-demand rejection,
uncalled type/borrow errors, valid changes and restoration. Bind all exact build
sources and binaries. The corrected native prototype has 381 bytecode controls
per profile; the complete candidate build requires 644 workspace controls per
profile and the complete Python suite before qualification.

For original diagnostic profiles, reuse the three closed adopted-VM profiles
from scratch-memory-values-profile-01 after exact binary/artifact/tape/source
bindings. Execute three new candidate profiles with the same checked entropy
tapes, validate complete same-process operation maps and exact original per-PC
logical counts, memory peaks and entropy accounting. This is correctness work;
profile timings are not performance measurements. Fresh baseline/candidate/A/A
commands remain mandatory for the later changed-source screen.

Keep the global lock, conservative 12 GiB qualification/profile admission,
two Cargo workers where applicable and the 8 GiB child floor. Preserve original
artifacts, failed attempts, installed tools, peer work and the paused goal.
