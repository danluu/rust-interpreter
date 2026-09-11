# Production edits and existing fre tests

Seventeen original forward-anchored tests newly executable with guest TLS destructors: ordered disjoint witness partitions, directed-position model comparisons, candidate-prefix accounting, threshold boundaries and exact call counts; real production edits preserve original tests and tracing instrumentation.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 5/5 complete-command pairs. The median paired candidate-minus-baseline difference is -0.062 s. Bytecode is identical in 0/5 pairs; both artifacts are retained for every pair. Per-edit Cargo and execution stages are retained in JSON.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

Baseline custom commands use `RUSTFLAGS=-Zmir-opt-level=1`; candidate commands use `RUSTFLAGS=-Zmir-opt-level=3`. Native retains its Cargo profile. Both configurations preserve strict checking. Exact per-mode flags and all resulting artifacts are retained.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.433 | 7.332 |
| baseline | 1.983 | 5.848 |
| candidate | 1.887 | 6.759 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
