# Production edits and existing pgrust tests

All four existing hashfn library unit tests, including the original 100,000-iteration roundtrip loop.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `interpreter` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 2/5 complete-command pairs. The median paired candidate-minus-baseline difference is +0.010 s. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 0.660 | 1.185 |
| baseline | 0.810 | 0.841 |
| candidate | 0.823 | 0.831 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.
