# Production edits and existing rg-aot tests

Existing private collection-boundary test after five production refactors.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 3/5 complete-command pairs. The median paired candidate-minus-baseline difference is -0.010 s. Bytecode is identical in 5/5 pairs; both artifacts are retained for every pair. Per-edit Cargo and execution stages are retained in JSON.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 0.546 | 4.305 |
| baseline | 0.208 | 2.825 |
| candidate | 0.200 | 2.842 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
