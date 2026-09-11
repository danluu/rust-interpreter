# Production edits and existing ruff tests

All six existing registry tests, including rule-code roundtrips, naming patterns, and linter sorting.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 9/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.022 s wall and +0.016 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.285 / -0.175 / +0.038 | -0.108 / +0.010 / +0.039 |
| 2 | 3 | -0.251 / -0.003 / +0.044 | -0.037 / +0.028 / +0.141 |
| 3 | 3 | -0.042 / +0.076 / +0.313 | -0.038 / +0.065 / +0.087 |
| 4 | 3 | -0.068 / -0.022 / +0.032 | -0.034 / -0.029 / +0.029 |
| 5 | 3 | -0.079 / -0.027 / +0.008 | -0.078 / +0.016 / +0.035 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 5.104 | 7.399 | 29.231 |
| baseline | 2.730 | 2.691 | 26.066 |
| candidate | 2.767 | 2.718 | 26.517 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=4. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 2.497 s wall / 2.432 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 2.074 | 0.099 | 0.005 | 0.009 | 0.004 | 0.006 |
| candidate | 2.126 | 0.099 | 0.005 | 0.009 | 0.004 | 0.006 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 5.268 | 2.783 | 2.717 |
| 2 | 5.274 | 2.826 | 2.717 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
