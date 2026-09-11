# Production edits and existing nushell tests

All four existing parser-keyword tests, including collection of single-word keywords.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 1/5 complete-command pairs. The median paired candidate-minus-baseline difference is +0.012 s. Bytecode is identical in 5/5 pairs; both artifacts are retained for every pair. Per-edit Cargo and execution stages are retained in JSON.

Test selection changes with each production edit. Each mode runs the same selection at each state; the exact selections are recorded in summary.json.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 0.677 | 22.197 |
| baseline | 0.467 | 20.619 |
| candidate | 0.460 | 21.388 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
