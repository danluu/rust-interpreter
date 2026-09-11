# Production edits and existing fre tests

All eighteen original folded-literal-trie tests, including complete short-byte-string/window differentials, malformed UTF-8, canonical folding, exact resource gates, SIMD prefilters and accounting.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 11/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.028 s wall and -0.033 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.051 / -0.042 / -0.030 | -0.050 / -0.047 / -0.033 |
| 2 | 3 | -0.041 / +0.027 / +0.044 | -0.035 / +0.023 / +0.040 |
| 3 | 3 | -0.038 / -0.015 / +0.037 | -0.033 / -0.009 / +0.036 |
| 4 | 3 | -0.027 / -0.026 / +0.008 | -0.033 / -0.028 / +0.001 |
| 5 | 3 | -0.042 / -0.038 / -0.028 | -0.046 / -0.037 / -0.030 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 1.638 | 2.079 | 6.885 |
| baseline | 2.500 | 2.478 | 7.046 |
| candidate | 2.485 | 2.463 | 7.219 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.636 s wall / 0.630 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.543 | 0.143 | 0.011 | 0.011 | 0.011 | 0.012 |
| candidate | 0.525 | 0.140 | 0.011 | 0.011 | 0.011 | 0.011 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 1.665 | 2.562 | 2.553 |
| 2 | 1.683 | 2.602 | 2.576 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
