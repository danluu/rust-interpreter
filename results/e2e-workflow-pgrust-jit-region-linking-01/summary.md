# Production edits and existing pgrust tests

All four existing hashfn library unit tests, including the original 100,000-iteration roundtrip loop.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 0.688 | 0.790 |
| interpreter | 0.759 | 0.792 |
| jit | 0.534 | 0.543 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
