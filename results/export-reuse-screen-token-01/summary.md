# Production edits and existing fre tests

The original exhaustive token-phrase byte-semantics test plus directed restart and route-boundary tests. The custom VM uses an explicit150000 live-allocation budget; native Cargo has its normal allocator. Five production-body refactors leave every original test unchanged..

Custom engines explicitly allow 150,000 live guest allocations and retain the 64 MiB guest-byte budget. Native Cargo uses its normal allocator.

5 cumulative production-body refactors across 1 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 5/5 complete-command pairs. The median paired candidate-minus-baseline difference is -0.261 s wall and -0.208 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 1 | -0.261 / -0.261 / -0.261 | -0.297 / -0.297 / -0.297 |
| 2 | 1 | -0.274 / -0.274 / -0.274 | -0.181 / -0.181 / -0.181 |
| 3 | 1 | -0.123 / -0.123 / -0.123 | -0.122 / -0.122 / -0.122 |
| 4 | 1 | -0.275 / -0.275 / -0.275 | -0.311 / -0.311 / -0.311 |
| 5 | 1 | -0.108 / -0.108 / -0.108 | -0.208 / -0.208 / -0.208 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

Host build scripts, procedural macros, and their build dependencies use optimization level 0 in every mode. Their first compilation is included in cold command times.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 2.214 | 2.718 | 7.459 |
| baseline | 4.835 | 4.793 | 9.729 |
| candidate | 4.667 | 4.603 | 9.772 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=4. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.804 s wall / 0.713 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.625 | 0.832 | 0.053 | 0.058 | 0.053 | 0.060 |
| candidate | 0.618 | 0.602 | 0.002 | 0.002 | 0.047 | 0.058 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 5 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

The baseline enables native Calls/Returns with guest-frame continuations.

The baseline enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
