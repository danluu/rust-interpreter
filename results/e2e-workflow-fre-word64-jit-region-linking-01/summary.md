# Production edits and existing fre tests

All twelve existing fixed-predicate word-matcher tests, including exhaustive reference comparisons.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 2.049 | 7.288 |
| interpreter | 15.316 | 19.405 |
| jit | 2.485 | 6.334 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
