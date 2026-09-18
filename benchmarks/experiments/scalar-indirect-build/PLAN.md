# Build the qualified indirect/scalar composition with the adopted compiler

Require closed focus02 (10 integration,3 metadata and355 library controls per
profile) and focus04 (3 complete-memory controls/profile). Preserve both failed
focus attempts. Build all workspace checks in both profiles:631 tests expected,
17 retained ignored diagnostics. Run431 Python contracts (409 pass,22 declared
skips), including both new launcher option controls, then build the release VM.
Freeze all Rust, Cargo, launcher, test and controller inputs. Exporter and wrapper
are copied byte-for-byte from adopted df4006e0; publish an immutable composition
key with kind scalar-indirect-calls only after every check passes.

Use only the shared ROOT target, two Cargo/test workers, global lock and
max(14 GiB,8 GiB+twice allocated target) build admission plus8 GiB child floor.
Record per-command setup time and terminal failures. No original-project timing
or adoption occurs. Then qualify strict checking/cache behavior, actual partial-
artifact rejection for each flag, and exact original profiles/code maps before
the unchanged full-token real-edit primary and conditional project/parser guards.
