# Production edits and existing fre tests

All six existing bounded class-sequence tests: greedy matching, scaling, accounting, and exact resource boundaries.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 2/5 complete-command pairs. The median paired candidate-minus-baseline difference is +0.021 s. Bytecode is identical in 5/5 pairs; both artifacts are retained for every pair. Per-edit Cargo and execution stages are retained in JSON.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.301 | 6.435 |
| baseline | 0.734 | 4.081 |
| candidate | 0.755 | 4.235 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
