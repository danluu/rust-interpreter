# Production edits and existing pgrust tests

All four existing hashfn library unit tests, including the original 100,000-iteration roundtrip loop.

5 cumulative production-body refactors across 1 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 3/5 complete-command pairs. The median paired candidate-minus-baseline difference is -0.006 s wall and -0.006 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 1 | -0.007 / -0.007 / -0.007 | -0.008 / -0.008 / -0.008 |
| 2 | 1 | -0.006 / -0.006 / -0.006 | -0.008 / -0.008 / -0.008 |
| 3 | 1 | +0.008 / +0.008 / +0.008 | +0.008 / +0.008 / +0.008 |
| 4 | 1 | +0.007 / +0.007 / +0.007 | +0.007 / +0.007 / +0.007 |
| 5 | 1 | -0.006 / -0.006 / -0.006 | -0.006 / -0.006 / -0.006 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.664 | 0.526 | 1.571 |
| baseline | 0.517 | 0.504 | 0.613 |
| candidate | 0.518 | 0.506 | 0.515 |

Native control: `repository`, 2 build jobs, `1` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=2, candidate=2. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.386 s wall / 0.380 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.016 | 0.008 | 0.000 | 0.000 | 0.000 | 0.000 |
| candidate | 0.016 | 0.009 | 0.000 | 0.000 | 0.000 | 0.000 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 5 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

The baseline enables native Calls/Returns with guest-frame continuations.

The baseline enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
