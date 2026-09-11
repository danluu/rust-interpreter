# Production edits and existing fre tests

The original exhaustive token-phrase byte-semantics test plus directed restart and route-boundary tests. The custom VM uses an explicit150000 live-allocation budget; native Cargo has its normal allocator. Five production-body refactors leave every original test unchanged..

Custom engines explicitly allow 150,000 live guest allocations and retain the 64 MiB guest-byte budget. Native Cargo uses its normal allocator.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 15/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.987 s wall and -0.955 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -1.098 / -0.987 / -0.913 | -1.069 / -0.970 / -0.918 |
| 2 | 3 | -1.023 / -0.969 / -0.788 | -0.973 / -0.955 / -0.937 |
| 3 | 3 | -1.291 / -1.030 / -0.627 | -1.112 / -0.917 / -0.863 |
| 4 | 3 | -1.099 / -0.981 / -0.602 | -1.008 / -0.899 / -0.886 |
| 5 | 3 | -1.280 / -1.223 / -0.751 | -1.103 / -1.029 / -0.918 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

Host build scripts, procedural macros, and their build dependencies use optimization level 0 in every mode. Their first compilation is included in cold command times.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 2.208 | 2.557 | 6.648 |
| baseline | 6.641 | 6.434 | 10.691 |
| candidate | 5.715 | 5.485 | 9.741 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.780 s wall / 0.655 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.610 | 0.581 | 0.048 | 0.055 | 0.050 | 0.053 |
| candidate | 0.634 | 0.593 | 0.049 | 0.055 | 0.051 | 0.054 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 2.148 | 6.541 | 5.709 |
| 2 | 2.182 | 6.736 | 5.714 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
