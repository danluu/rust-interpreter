# Instrumented production edits and existing nushell tests

All fourteen existing type-relation tests: enum cross-product covariance, OneOf hashing/deduplication, nested collections, and the original 100-step widening chain.

This diagnostic records Cargo unit timings and child user/system CPU, fault and context-switch counters. It is kept separate from uninstrumented performance qualification.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Every mode enables Cargo unit timing reports. Report generation is included in the command time; snapshot copying follows the timer. Snapshot paths and hashes are recorded with each sample.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 2/5 complete-command pairs. The median paired candidate-minus-baseline difference is +0.239 s. Bytecode is identical in 0/5 pairs; both artifacts are retained for every pair. Per-edit Cargo and execution stages are retained in JSON.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 9.827 | 72.676 |
| baseline | 5.737 | 64.632 |
| candidate | 6.016 | 69.831 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
