# Integrate the qualified scratch-value/scalar-call composition

Preserve main's optional runtime-compiler prepublication validation and all its
tests. Carry the exact bytecode sources, launcher, and profiling helpers from
`b462d9e6`, including the scalar-option launcher test. No compiler or runtime
algorithm changes belong in this integration.

Before adoption, verify complete Rust/Cargo/configuration input equality with
the measured candidate and the installed VM/exporter/wrapper digests. Among
production Python scripts only `runtime_compiler.py` may differ; it must match
main `701cc006`. The stock launcher does not import that optional installation
module. Verify the closed result summaries, terminals, raw command records and
source/evidence manifests for the 608 Rust tests per profile, 121 strict/cache
commands, six exact profiles, 13 real controls, 726 performance commands and
both 88-command full-parser histories. These are reused evidence, not fresh
executions or new timings. Original logs and artifacts remain retained.

Run the full merged Python contract suite once, with its scalar-option and
runtime-compiler validation tests. Require success; report actual executed and
skipped counts. Freeze all tracked Python files and all tracked scripts, tests,
Rust and configuration inputs before execution and verify afterward. Use the
shared benchmark lock, an 8 GiB child floor and the exact task-owned supervisor.
This check creates no large compiler cache and runs no performance benchmark.

Adopt only after that check passes. Keep `--jit-scalar-calls` explicit, requiring
the resumable JIT and a fully checked artifact; preserve strict type/borrow
checking, normal entropy and the 16 MiB arena. Update the current-state documents
with the measured composition and native gaps, then push the qualified merge.
Next collect owned native-PC samples on the newly adopted VM before selecting
another runtime mechanism. Compiler/Cargo work remains with the other session.
