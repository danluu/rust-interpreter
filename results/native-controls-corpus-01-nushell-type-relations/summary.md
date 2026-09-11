# Production edits and existing nushell tests

All fourteen existing type-relation tests: enum cross-product covariance, OneOf hashing/deduplication, nested collections, and the original 100-step widening chain.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 10/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.034 s wall and -0.020 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.345 / +0.003 / +0.015 | -0.020 / +0.101 / +0.127 |
| 2 | 3 | -0.061 / -0.061 / +0.542 | -0.145 / -0.098 / +0.273 |
| 3 | 3 | -0.289 / -0.017 / +0.669 | -0.576 / +0.045 / +0.436 |
| 4 | 3 | -0.756 / -0.079 / -0.001 | -1.047 / -0.179 / -0.013 |
| 5 | 3 | -0.543 / -0.034 / +0.117 | -0.992 / -0.103 / +0.228 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 8.303 | 22.397 | 48.721 |
| baseline | 4.899 | 7.710 | 65.482 |
| candidate | 4.704 | 7.612 | 68.162 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 4.069 s wall / 7.134 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 1.010 | 0.070 | 0.002 | 0.002 | 0.002 | 0.002 |
| candidate | 0.998 | 0.071 | 0.002 | 0.002 | 0.002 | 0.002 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 14.450 | 5.710 | 6.022 |
| 2 | 11.298 | 4.175 | 4.241 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
