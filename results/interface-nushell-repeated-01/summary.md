# Production edits and existing nushell tests

Generalize the public Type::list constructor to Into<Type>. Existing constructor, covariance and OneOf assertions remain unchanged across all fourteen selected type-relation tests..

1 cumulative production-body refactors across 15 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 7/15 complete-command pairs. The median paired candidate-minus-baseline difference is +0.056 s wall and +0.040 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 15 | -0.652 / +0.056 / +0.671 | -0.931 / +0.040 / +0.829 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 12.689 | 37.008 | 38.370 |
| baseline | 5.504 | 8.398 | 63.051 |
| candidate | 5.500 | 8.416 | 62.074 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 4.433 s wall / 7.612 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 1.138 | 0.078 | 0.002 | 0.002 | 0.002 | 0.002 |
| candidate | 1.130 | 0.079 | 0.002 | 0.002 | 0.002 | 0.002 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 11.926 | 4.224 | 4.364 |
| 2 | 12.455 | 5.521 | 5.191 |
| 3 | 13.834 | 5.693 | 5.366 |
| 4 | 15.105 | 7.252 | 7.080 |
| 5 | 12.164 | 4.973 | 5.420 |
| 6 | 13.274 | 5.800 | 6.140 |
| 7 | 12.142 | 5.812 | 5.005 |
| 8 | 10.964 | 4.400 | 4.470 |
| 9 | 11.304 | 4.571 | 5.006 |
| 10 | 11.491 | 4.702 | 5.469 |
| 11 | 12.864 | 5.347 | 4.812 |
| 12 | 11.706 | 4.594 | 5.243 |
| 13 | 12.223 | 4.519 | 4.673 |
| 14 | 13.599 | 5.862 | 5.818 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
