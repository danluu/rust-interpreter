# Production edits and existing fre tests

Six existing packed literal-set tests covering SIMD matcher, factored byte classes, windows, resource accounting and shape refusal; the seventh regex-reference test remains lowering-blocked..

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.508 | 6.913 |
| interpreter | 0.971 | 4.731 |
| jit | 0.951 | 4.624 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
