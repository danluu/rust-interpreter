# Production edits and existing nushell tests

Generalize the public Type::list constructor to Into<Type>. Existing constructor, covariance and OneOf assertions remain unchanged across all fourteen selected type-relation tests..

1 cumulative production-body refactors across 15 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 15/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.214 s wall and -0.143 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 15 | -0.595 / -0.214 / -0.047 | -0.462 / -0.143 / +0.023 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 11.972 | 32.325 | 42.223 |
| baseline | 5.150 | 7.386 | 64.437 |
| candidate | 4.963 | 7.268 | 64.102 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 4.291 s wall / 6.991 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 1.066 | 0.072 | 0.002 | 0.002 | 0.002 | 0.002 |
| candidate | 1.044 | 0.070 | 0.002 | 0.002 | 0.002 | 0.002 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 11.808 | 5.047 | 4.913 |
| 2 | 11.780 | 4.997 | 4.831 |
| 3 | 11.214 | 4.870 | 4.902 |
| 4 | 11.329 | 4.917 | 4.745 |
| 5 | 11.078 | 5.009 | 4.660 |
| 6 | 11.229 | 5.032 | 4.850 |
| 7 | 11.203 | 4.896 | 4.831 |
| 8 | 11.506 | 5.182 | 4.900 |
| 9 | 11.611 | 5.239 | 4.922 |
| 10 | 12.074 | 5.246 | 4.981 |
| 11 | 12.004 | 5.195 | 4.922 |
| 12 | 12.781 | 5.313 | 5.046 |
| 13 | 12.254 | 5.178 | 4.904 |
| 14 | 12.589 | 5.386 | 5.072 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
