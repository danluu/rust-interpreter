# Production edits and existing rg-aot tests

Existing private collection-boundary test after five production refactors.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 0.538 | 3.853 |
| interpreter | 0.196 | 2.887 |
| jit | 0.194 | 2.894 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
