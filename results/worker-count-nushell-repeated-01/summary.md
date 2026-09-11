# Production edits and existing nushell tests

Generalize the public Type::list constructor to Into<Type>. Existing constructor, covariance and OneOf assertions remain unchanged across all fourteen selected type-relation tests..

1 cumulative production-body refactors across 15 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 5/15 complete-command pairs. The median paired candidate-minus-baseline difference is +0.026 s wall and +0.554 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 15 | -0.427 / +0.026 / +0.322 | -0.167 / +0.554 / +1.150 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 12.366 | 35.249 | 40.775 |
| baseline | 5.288 | 7.996 | 66.704 |
| candidate | 5.280 | 8.476 | 39.389 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=18. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 4.393 s wall / 7.126 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 1.115 | 0.071 | 0.002 | 0.002 | 0.002 | 0.002 |
| candidate | 1.094 | 0.072 | 0.002 | 0.002 | 0.002 | 0.002 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 11.929 | 4.739 | 4.646 |
| 2 | 12.088 | 5.279 | 4.712 |
| 3 | 13.099 | 5.545 | 5.210 |
| 4 | 10.812 | 4.775 | 4.798 |
| 5 | 10.542 | 4.279 | 4.274 |
| 6 | 10.798 | 4.223 | 4.805 |
| 7 | 10.946 | 4.224 | 4.326 |
| 8 | 12.757 | 5.338 | 5.803 |
| 9 | 13.971 | 5.742 | 5.987 |
| 10 | 11.798 | 4.959 | 5.398 |
| 11 | 12.088 | 4.835 | 4.872 |
| 12 | 11.503 | 4.998 | 5.144 |
| 13 | 11.957 | 4.512 | 4.560 |
| 14 | 12.074 | 5.252 | 5.256 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
