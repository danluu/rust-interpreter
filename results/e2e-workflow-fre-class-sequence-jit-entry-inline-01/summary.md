# Production edits and existing fre tests

All six existing bounded class-sequence tests: greedy matching, scaling, accounting, and exact resource boundaries.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.325 | 6.622 |
| interpreter | 0.760 | 4.241 |
| jit | 0.729 | 4.298 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
