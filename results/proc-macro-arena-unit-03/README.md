# Actual Arena unit tests

All nine tests from the actual proposed Arena03 source passed with the installed
Rust 1.100.0 nightly dated 2026-09-08. The source wrapper includes that module
directly without substitutes or compatibility shims. Compilation and execution
completed under the canonical workload lock; both compiler output streams and
the test stderr were empty. The exact commands, source digests, compiler version,
child identities, closure, and raw results are retained here.

This small standalone unit build produced a 1,122,648-byte executable in its own
work directory. It used a 9 GiB free-space admission floor and 64 MiB per-file
limits, separate from the unchanged 24 GiB full runtime-build requirement.
No application, benchmark, compiler integration, Miri, or Interner test ran in
this invocation. Passing these tests does not establish soundness or a speedup.
