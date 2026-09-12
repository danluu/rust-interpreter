# Production edits and existing pgrust tests

All four existing hashfn library unit tests, including the original 100,000-iteration roundtrip loop.

5 cumulative production-body refactors across 1 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 2/5 complete-command pairs. The median paired candidate-minus-baseline difference is +0.004 s wall and +0.004 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 1 | -0.011 / -0.011 / -0.011 | -0.010 / -0.010 / -0.010 |
| 2 | 1 | +0.005 / +0.005 / +0.005 | +0.004 / +0.004 / +0.004 |
| 3 | 1 | +0.015 / +0.015 / +0.015 | +0.014 / +0.014 / +0.014 |
| 4 | 1 | +0.004 / +0.004 / +0.004 | +0.004 / +0.004 / +0.004 |
| 5 | 1 | -0.005 / -0.005 / -0.005 | -0.005 / -0.005 / -0.005 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.697 | 0.547 | 1.246 |
| baseline | 0.511 | 0.496 | 1.078 |
| candidate | 0.514 | 0.500 | 0.537 |

Native control: `repository`, 2 build jobs, `1` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=2, candidate=2. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.387 s wall / 0.382 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.015 | 0.008 | 0.000 | 0.000 | 0.000 | 0.000 |
| candidate | 0.016 | 0.008 | 0.000 | 0.000 | 0.000 | 0.000 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 5 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

The baseline enables native Calls/Returns with guest-frame continuations.

The baseline enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
