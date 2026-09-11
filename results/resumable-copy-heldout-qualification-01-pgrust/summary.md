# Production edits and existing pgrust tests

All four existing hashfn library unit tests, including the original 100,000-iteration roundtrip loop.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 15/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.024 s wall and -0.026 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.046 / -0.024 / -0.011 | -0.045 / -0.026 / -0.010 |
| 2 | 3 | -0.028 / -0.016 / -0.015 | -0.028 / -0.017 / -0.016 |
| 3 | 3 | -0.024 / -0.015 / -0.002 | -0.024 / -0.014 / -0.001 |
| 4 | 3 | -0.060 / -0.034 / -0.024 | -0.060 / -0.034 / -0.026 |
| 5 | 3 | -0.042 / -0.037 / -0.027 | -0.042 / -0.038 / -0.026 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.661 | 0.605 | 1.650 |
| baseline | 0.473 | 0.464 | 0.530 |
| candidate | 0.448 | 0.438 | 0.485 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=4. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.370 s wall / 0.363 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.015 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 |
| candidate | 0.015 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 0.665 | 0.469 | 0.443 |
| 2 | 0.678 | 0.480 | 0.443 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.
