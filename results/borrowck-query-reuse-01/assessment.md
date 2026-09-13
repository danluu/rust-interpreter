# Compiler-proven borrow-check result reuse

The optional `--borrowck-cache verify|reuse` implementation passes its
correctness qualification: 80 Rust exporter/routing tests, 56 Python launcher
tests, nine direct compiler tests and one Cargo integration test. The compiled
implementation was committed as `11537c7`; the final test source hashes and binary
identities are in [the summary](summary.json).

No performance benchmark was run. Nushell source and manifests were unchanged,
and the option remains off by default. These tests demonstrate avoided provider
executions, not faster complete builds or a sub-0.5-second Nushell build.

The positive direct-compiler observations are:

| Edited fixture | Mode | Green candidates | Empty results reconstructed | Original results verified | Nonempty fallbacks |
| --- | --- | ---: | ---: | ---: | ---: |
| Existing private functions become reachable, ordinary O0 | reuse | 4 | 3 | 0 | 1 |
| Same newly reachable history | verify | 4 | 0 | 3 | 1 |
| Inlined callee changes, selected test with MIR level 3 | reuse | 4 | 3 | 0 | 1 |
| Following inlined-callee edit | verify | 3 | 0 | 2 | 1 |

Unchanged optimized MIR normally reloads from rustc's existing cache and avoids
these value demands altogether. Ordinary cached edits therefore showed zero
opportunities. In the selected-test fixture, changing a one-digit literal to
two digits also shifted later source positions and made rustc rerun additional
providers. The implementation preserves that invalidation.

Native outputs and structured diagnostics match the controls, including unused
functions with type/borrow errors, opaque return types, dependency constants,
macros and trait changes, warnings, lint expectations and restoration after
failed builds. Selected bytecode matches the off-mode exporter and executes in
the interpreter. Positive native histories also enable rustc's incremental hash
verification. Diagnostic modes, NLL fact output, internal attributes and the
nondefault legacy Polonius checker exercise bypasses; native total-time text is
checked only as a diagnostic-output feature, without assessing its values.

The Cargo smoke builds local dependencies and a native build script, consumes
its generated constant, exports library and test entries, checks metadata
sidecars and interpreter output, rejects an invalid unused function and verifies
restored output. It covers both an explicit pinned compiler and ordinary
`cargo +nightly-2026-09-08` with `RUSTC` unset. Cached dependency stderr can replay
old cache reports, so the smoke requires the selected unit's report and the
table above uses only direct compiler observations.

Qualification is composed from three retained scopes: the Rust/build/launcher
commands in run03, all nine direct compiler tests in run05, and the complete
Cargo test in run07. Earlier failed fixture assumptions are retained in the
logs and summary: expecting cache hits beneath already cached MIR, assuming
Polonius-next was nondefault, expecting one provider call after a span shift,
and expecting JSON compiler errors with Cargo's `json-render-diagnostics` mode.
No implementation changes were needed after that build. The
[source snapshot](build-source-snapshot.json) records the candidate files while
the build supervisor was queued; its receipt's earlier HEAD is the queue-time
base, not a claim that the unmodified base produced the tested binaries.

All builds and tests held the shared repository lock. The draft was pushed
while waiting for another session's workload; no unrelated process was altered.
The [196 command receipts](commands.jsonl.gz) retain exact arguments, return
codes, output and diagnostics for the final direct/compiler and Cargo scopes.
They are correctness evidence, with no new performance estimate.

See [the mechanism and remaining compiler work](../../docs/BORROWCK-REUSE.md).
