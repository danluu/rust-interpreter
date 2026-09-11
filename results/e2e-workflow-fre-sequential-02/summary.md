# Production edits and three existing fre codec tests

Five cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production encoding. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the three selected tests in one command. Custom engines use three serial launcher commands, reflecting the initial interface.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.308 | 6.480 |
| interpreter | 2.105 | 13.042 |
| jit | 2.110 | 12.819 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
