# Production edits and three existing fre codec tests

Five cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production encoding. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the three selected tests in one command. Custom engines use one command.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.314 | 6.754 |
| interpreter | 0.721 | 4.279 |
| jit | 0.714 | 4.314 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
