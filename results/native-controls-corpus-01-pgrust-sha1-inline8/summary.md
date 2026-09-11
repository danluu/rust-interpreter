# Production edits and existing pgrust tests

Both existing SHA-1 unit tests: standard vectors including the original million-byte input, plus incremental hashing in seven-byte chunks.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 8/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.000 s wall and +0.000 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.001 / +0.005 / +0.045 | -0.001 / +0.006 / +0.039 |
| 2 | 3 | -0.003 / -0.001 / +0.095 | -0.004 / -0.003 / +0.007 |
| 3 | 3 | -0.031 / -0.000 / +0.020 | -0.030 / +0.000 / +0.018 |
| 4 | 3 | -0.008 / -0.003 / +0.032 | -0.009 / -0.003 / +0.030 |
| 5 | 3 | -0.017 / +0.005 / +0.010 | -0.016 / +0.001 / +0.010 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.756 | 0.754 | 0.928 |
| baseline | 0.755 | 0.741 | 0.846 |
| candidate | 0.756 | 0.739 | 0.827 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.393 s wall / 0.384 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.016 | 0.016 | 0.001 | 0.001 | 0.001 | 0.001 |
| candidate | 0.016 | 0.016 | 0.001 | 0.001 | 0.001 | 0.001 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 0.762 | 0.748 | 0.756 |
| 2 | 0.751 | 0.758 | 0.754 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
