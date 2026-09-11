# Identical-tool control with existing nushell tests

All fourteen existing type-relation tests: enum cross-product covariance, OneOf hashing/deduplication, nested collections, and the original 100-step widening chain.

Both custom slots execute the same installed tool, guest flags and original tests, using independent Cargo caches. Each engine runs its own complete cold/wrong/five-edit trajectory consecutively. Phase order is recorded; mode_orders gives relative ordering across phases, not adjacent commands. This is a variation control, not a candidate performance result. The binary file paths are shared between slots.

5 cumulative production-body refactors; test source is unchanged. Every mode first rejected a wrong production edit. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 0/5 complete-command pairs. The median paired candidate-minus-baseline difference is +1.141 s. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Mode | Median edited workflow seconds | Cold workflow seconds |
|---|---:|---:|
| native | 6.955 | 78.164 |
| baseline | 4.807 | 69.824 |
| candidate | 5.949 | 65.038 |

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. Five samples on a shared host are not a confidence interval or a whole-suite result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
