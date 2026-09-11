# Production edits and existing rg-aot tests

Existing private collection-boundary test after five production refactors.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 15/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.017 s wall and -0.019 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.027 / -0.022 / -0.015 | -0.026 / -0.021 / -0.019 |
| 2 | 3 | -0.040 / -0.017 / -0.013 | -0.021 / -0.017 / -0.014 |
| 3 | 3 | -0.026 / -0.016 / -0.008 | -0.025 / -0.017 / -0.010 |
| 4 | 3 | -0.028 / -0.027 / -0.017 | -0.028 / -0.026 / -0.018 |
| 5 | 3 | -0.022 / -0.017 / -0.016 | -0.021 / -0.018 / -0.012 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.538 | 0.808 | 3.603 |
| baseline | 0.195 | 0.184 | 2.953 |
| candidate | 0.175 | 0.165 | 2.808 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=4. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.090 s wall / 0.084 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.050 | 0.014 | 0.001 | 0.001 | 0.001 | 0.001 |
| candidate | 0.049 | 0.014 | 0.001 | 0.001 | 0.001 | 0.001 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 0.535 | 0.195 | 0.168 |
| 2 | 0.546 | 0.191 | 0.171 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.
