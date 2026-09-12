# Filtered suites in one checked compiler invocation

Discovery is qualified and published. Add `--test-filter PATTERN` as an alternative
to manual entries; substring matching follows native libtest's common filter
behavior, with optional `--test-exact`. An empty pattern selects all ordinary
nonignored tests. Require the existing explicit isolated JIT mode and new suite
report path. Preserve its separate guest state and fresh/prepared comparison.

Select from rustc's checked built-in descriptors inside the same invocation that
lowers the chosen graph. No preliminary listing command, extra full frontend
pass or native executable is needed. Match names before applying attributes.
Skip ignored tests, including ignored expected-panic tests. If any remaining
matched test requires expected-panic semantics, reject the entire selection
before lowering or executing anything. Reject zero runnable tests and more than
256 with clear errors; never report a passing suite that executed zero tests.
Keep a single selected test supported through an explicit one-entry catalog and
synthetic root, preserving the existing manual single-function representation.

Publish an 8 MiB bounded selection sidecar with full discovery metadata, exact
filter, selected names, skipped ignored names, and the exported bytecode digest.
The launcher independently verifies filtering and the digest against Cargo's
exact selected artifact and requires the matching entry catalog. Record selection
provenance in launch statistics. Track both filter pattern and matching mode in
rustc environment dependencies so source, feature, target and filter changes
invalidate the right metadata. Do not change unchecked/deferred semantics.

Qualify Rust debug/release and Python tests, then actual Cargo controls: substring
and exact selection, root/nested duplicate names, single Result test, ignored and
expected-panic handling, empty/oversized selections, feature and target changes,
unused borrow errors, wrong production edits and restored original assertions.
Use pgrust's full four-test suite and fre's real token/folded filters in edited
commands. Compare automatic vs explicit names with identical compiled bytecode,
limits, native assertions and effective reports. Keep separate descriptive timing
of whole edited commands; unchanged builds are not the objective. Two workers,
45-second global-lock waits and the 8 GiB child floor remain in force.
