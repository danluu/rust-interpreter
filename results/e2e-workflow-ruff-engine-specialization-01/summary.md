# Production edits and existing ruff tests

All six existing registry tests, including rule-code roundtrips, naming patterns, and linter sorting.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Test selection changes with each production edit. Each mode runs the same selection at each state; the exact selections are recorded in summary.json.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 5.761 | 63.714 |
| interpreter | 3.023 | 30.473 |
| jit | 3.026 | 28.201 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
