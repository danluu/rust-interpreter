# Production edits and existing fre tests

All six existing bounded class-sequence tests: greedy matching, scaling, accounting, and exact resource boundaries.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.421 | 6.847 |
| interpreter | 0.777 | 4.284 |
| jit | 0.811 | 4.234 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
