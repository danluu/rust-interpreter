# Production edits and existing ruff tests

All six existing registry tests, including rule-code roundtrips, naming patterns, and linter sorting.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Test selection changes with each production edit. Each mode runs the same selection at each state; the exact selections are recorded in summary.json.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 5.601 | 55.866 |
| interpreter | 3.113 | 27.752 |
| jit | 2.867 | 28.832 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
