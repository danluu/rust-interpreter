# Production edits and existing fre tests

All twelve existing fixed-predicate word-matcher tests, including exhaustive reference comparisons.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 2/5 complete-command pairs. The median paired candidate-minus-baseline difference is +0.010 s. Identical bytecode is required and verified. Per-edit Cargo and execution stages are retained in JSON.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 1.995 | 7.729 |
| baseline | 2.682 | 6.853 |
| candidate | 2.659 | 6.719 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
