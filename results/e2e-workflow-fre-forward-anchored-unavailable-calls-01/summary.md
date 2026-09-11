# Production edits and existing fre tests

All eleven newly executable forward-anchored original tests, including the exhaustive arbitrary-class/suffix differential, windows, canonical class selection, exact limits and work accounting; unavailable-call stops are explicit and reached boundaries are failures.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.523 | 6.918 |
| interpreter | 5.677 | 9.360 |
| jit | 1.694 | 5.107 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
