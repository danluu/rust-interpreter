# Allocation trace debug qualification

All 272 workspace tests pass, with one existing ignored test. The four new
trace tests cover ordered records and artifact binding, escaped data, exact
byte/newline and event limits, rollback and sticky failure. Frozen Rust inputs
remain unchanged; supervisor 62012/controller 62024 finished successfully.

The opt-in exporter records allocation origins, complete compiler instance
kinds, initialization masks, static/TLS identities and pre-rebase relocation
edges. It preserves the existing traversal and emits a bounded diagnostic
separate from bytecode. Strict checking remains required. This workspace check
does not yet establish unchanged bytecode or runtime results when tracing is
toggled; release installation and the original-fixture comparison are next.

See [test receipt](summary.json) and
[design](../../benchmarks/experiments/artifact-diff/CONSTANT-IDENTITY-NEXT.md).
