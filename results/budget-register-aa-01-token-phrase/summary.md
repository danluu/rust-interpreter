# Production edits and existing fre tests

The original exhaustive token-phrase byte-semantics test plus directed restart and route-boundary tests. The custom VM uses an explicit150000 live-allocation budget; native Cargo has its normal allocator. Five production-body refactors leave every original test unchanged..

Custom engines explicitly allow 150,000 live guest allocations and retain the 64 MiB guest-byte budget. Native Cargo uses its normal allocator.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 9/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.000 s wall and -0.025 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.112 / -0.034 / -0.000 | -0.086 / -0.050 / -0.005 |
| 2 | 3 | -0.129 / +0.034 / +0.107 | -0.049 / -0.047 / +0.114 |
| 3 | 3 | -0.093 / -0.000 / +0.180 | -0.040 / -0.036 / +0.084 |
| 4 | 3 | -0.070 / -0.030 / +0.037 | -0.025 / +0.004 / +0.072 |
| 5 | 3 | -0.269 / +0.007 / +0.169 | -0.081 / +0.024 / +0.078 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

Host build scripts, procedural macros, and their build dependencies use optimization level 0 in every mode. Their first compilation is included in cold command times.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 2.046 | 2.490 | 6.691 |
| baseline | 4.571 | 4.500 | 9.010 |
| candidate | 4.571 | 4.506 | 9.140 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=4. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.738 s wall / 0.662 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.554 | 0.787 | 0.051 | 0.057 | 0.047 | 0.055 |
| candidate | 0.556 | 0.792 | 0.051 | 0.057 | 0.050 | 0.055 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 2.074 | 4.969 | 4.732 |
| 2 | 1.965 | 4.484 | 4.790 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

The baseline enables native Calls/Returns with guest-frame continuations.

The baseline enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
