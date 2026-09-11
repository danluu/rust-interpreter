# Production edits and existing nushell tests

Seven existing fractional, decreasing, and rounded floating-point range tests.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 6.413 | 66.528 |
| interpreter | 3.954 | 54.402 |
| jit | 3.946 | 56.548 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
