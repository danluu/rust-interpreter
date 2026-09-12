# Qualified compiler integration

Source `5b2330c` reproduces qualified tool `9637b0ac` through a normal root
workspace build. All three executable SHA256 hashes match the previously
measured tool exactly. Debug and release each pass 289 workspace tests, with
one ignored diagnostic, in a fresh target directory.

The ordinary launcher selects this source key and verifies the existing tool
without rebuilding or replacing any installed file. The Git-backed build index
now reconstructs this source key. Execution receipts bind the completed
supervisor, controller, commands, logs and frozen source files.

This integrates the [qualified aggregate-frame compiler](../aggregate-relocation-e2e-01/assessment.md).
Its seven [held-out workflows](../aggregate-relocation-heldout-recovery-01/assessment.md)
and broad execution qualification apply to these exact binaries. Integration
itself is a reproducibility check, not a new performance measurement.

The VM and wrapper remain byte-identical to the preceding tool. The x22 budget
ABI [failed its fixed primary gate](../budget-register-primary-01/assessment.md)
and remains an isolated experiment. Runtime options remain explicit; this
selected-body engine does not provide full libtest, unwinding, threads or
general OS/FFI support.
