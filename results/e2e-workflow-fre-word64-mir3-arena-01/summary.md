# Production edits and existing fre tests

All twelve existing fixed-predicate word-matcher tests, including exhaustive reference comparisons.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Custom engines explicitly use `-Zmir-opt-level=3` for target compilation. Native uses its unchanged Cargo development/test profile. This changes MIR optimization without disabling overflow checks or frontend checking.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 2.081 | 7.082 |
| interpreter | 18.017 | 21.759 |
| jit | 5.731 | 9.787 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
