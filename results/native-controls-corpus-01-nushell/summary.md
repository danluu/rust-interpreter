# Production edits and existing nushell tests

All four existing parser-keyword tests, including collection of single-word keywords.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 10/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.006 s wall and -0.004 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.014 / -0.011 / -0.007 | -0.013 / -0.008 / -0.005 |
| 2 | 3 | -0.006 / +0.008 / +0.014 | -0.006 / +0.008 / +0.023 |
| 3 | 3 | -0.010 / +0.005 / +0.006 | -0.004 / +0.005 / +0.012 |
| 4 | 3 | -0.009 / -0.002 / -0.001 | -0.007 / -0.001 / +0.001 |
| 5 | 3 | -0.017 / -0.008 / +0.005 | -0.017 / -0.012 / +0.005 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.646 | 0.727 | 17.420 |
| baseline | 0.441 | 0.418 | 22.169 |
| candidate | 0.431 | 0.416 | 22.595 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.271 s wall / 0.263 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.095 | 0.018 | 0.001 | 0.001 | 0.001 | 0.001 |
| candidate | 0.092 | 0.018 | 0.001 | 0.001 | 0.001 | 0.001 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 0.631 | 0.444 | 0.447 |
| 2 | 0.680 | 0.441 | 0.451 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
