# Production edits and existing nushell tests

All fourteen existing type-relation tests: enum cross-product covariance, OneOf hashing/deduplication, nested collections, and the original 100-step widening chain.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 9/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.059 s wall and -0.179 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.102 / +0.015 / +0.094 | -0.451 / -0.160 / -0.105 |
| 2 | 3 | -0.059 / -0.041 / +0.631 | -0.317 / -0.264 / +0.223 |
| 3 | 3 | -0.627 / -0.397 / +0.104 | -0.663 / -0.179 / -0.114 |
| 4 | 3 | -0.205 / -0.123 / +0.105 | -0.262 / -0.222 / -0.076 |
| 5 | 3 | -0.215 / -0.095 / +0.806 | -0.424 / -0.033 / +0.230 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 7.913 | 20.924 | 43.548 |
| baseline | 4.873 | 7.316 | 63.992 |
| candidate | 4.849 | 7.084 | 62.199 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=4. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 4.153 s wall / 6.923 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 1.036 | 0.069 | 0.002 | 0.002 | 0.002 | 0.002 |
| candidate | 1.046 | 0.070 | 0.002 | 0.002 | 0.002 | 0.002 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 11.813 | 4.802 | 4.814 |
| 2 | 12.034 | 4.985 | 4.663 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
