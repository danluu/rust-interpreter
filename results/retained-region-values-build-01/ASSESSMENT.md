# Immutable retained-value candidate built

All 615 workspace tests/profile pass in debug and release (13 retained ignored
diagnostics). Python discovers 429 tests: 407 pass and 22 skip. Four commands
complete in 124.43 seconds of setup, separate from performance measurements.

The immutable candidate key is
`76345e9c49cf908287c4dd395db9f59fb06b2c987d83ea26647d989b52ed1dbd`,
with VM `bfbb53e26705993c9020f171add5053a030a7edd08e68460a50875abe2eaee9f`.
Exporter and wrapper are byte-identical to adopted `df4006e0`; the candidate
changes only the custom VM. The closure binds 476 inputs and 14 retained artifacts.

Proceed through the frozen strict, original-profile and primary protocols.
This build is not an adoption or speedup result. Source `6ebe2288`;
[summary.json](summary.json) and [closure.json](closure.json) retain exact setup,
binary and source bindings.
