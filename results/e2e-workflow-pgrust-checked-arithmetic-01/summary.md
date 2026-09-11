# Production edits and existing pgrust tests

All four existing hashfn library unit tests, including the original 100,000-iteration roundtrip loop.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 0.661 | 0.813 |
| interpreter | 0.816 | 0.839 |
| jit | 0.546 | 0.544 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
