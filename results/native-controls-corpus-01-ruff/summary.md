# Production edits and existing ruff tests

All six existing registry tests, including rule-code roundtrips, naming patterns, and linter sorting.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 10/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.067 s wall and -0.019 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.170 / +0.015 / +0.036 | +0.041 / +0.043 / +0.044 |
| 2 | 3 | -0.010 / -0.004 / +0.387 | -0.019 / -0.003 / +0.104 |
| 3 | 3 | -0.160 / -0.137 / -0.067 | -0.136 / -0.063 / -0.042 |
| 4 | 3 | -0.258 / -0.171 / +0.038 | -0.203 / -0.186 / +0.026 |
| 5 | 3 | -0.226 / -0.070 / +0.126 | -0.121 / -0.082 / +0.082 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 5.760 | 8.357 | 26.943 |
| baseline | 3.146 | 3.049 | 30.233 |
| candidate | 3.007 | 2.968 | 28.688 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 2.720 s wall / 2.654 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 2.391 | 0.117 | 0.005 | 0.010 | 0.005 | 0.006 |
| candidate | 2.304 | 0.112 | 0.005 | 0.009 | 0.004 | 0.006 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 5.673 | 2.907 | 2.950 |
| 2 | 6.067 | 3.139 | 3.024 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
