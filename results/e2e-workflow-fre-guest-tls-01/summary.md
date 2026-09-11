# Production edits and existing fre tests

Seventeen original forward-anchored tests newly executable with guest TLS destructors: ordered disjoint witness partitions, directed-position model comparisons, candidate-prefix accounting, threshold boundaries and exact call counts; real production edits preserve original tests and tracing instrumentation.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.884 | 7.046 |
| interpreter | 10.625 | 14.188 |
| jit | 2.422 | 5.854 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
