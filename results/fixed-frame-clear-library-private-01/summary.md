# Production edits and existing rg-aot tests

Existing private collection-boundary test after five production refactors.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 6/15 complete-command pairs. The median paired candidate-minus-baseline difference is +0.000 s wall and -0.000 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.006 / -0.001 / +0.004 | -0.003 / -0.001 / +0.001 |
| 2 | 3 | +0.000 / +0.002 / +0.008 | +0.001 / +0.001 / +0.007 |
| 3 | 3 | +0.000 / +0.001 / +0.013 | -0.002 / +0.002 / +0.012 |
| 4 | 3 | -0.011 / -0.005 / -0.001 | -0.008 / -0.005 / -0.000 |
| 5 | 3 | -0.001 / +0.001 / +0.003 | -0.001 / -0.001 / +0.001 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.533 | 0.772 | 3.482 |
| baseline | 0.180 | 0.169 | 2.870 |
| candidate | 0.181 | 0.171 | 2.842 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=4. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.091 s wall / 0.086 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.049 | 0.018 | 0.001 | 0.001 | 0.001 | 0.001 |
| candidate | 0.050 | 0.017 | 0.001 | 0.001 | 0.001 | 0.001 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 0.540 | 0.171 | 0.174 |
| 2 | 0.511 | 0.173 | 0.170 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

The baseline enables native Calls/Returns with guest-frame continuations.

The baseline enables persistent full-width native registers.
