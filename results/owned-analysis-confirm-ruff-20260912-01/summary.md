# Production edits and existing ruff tests

All six existing registry tests, including rule-code roundtrips, naming patterns, and linter sorting.

Custom engines explicitly allow 150,000 live guest allocations and retain the 64 MiB guest-byte budget. Native Cargo uses its normal allocator.

5 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

After source restoration completed, every mode freshly compiled and executed the original tests. These final controls are excluded from edited medians and pairs.

Build-to-ready measurements end after the launcher validates the selected artifact and before VM invocation. CPU includes launcher self and its waited-for build children; no VM execution time is subtracted.

| Mode | Median edited build-to-ready wall, s | Median edited build-to-ready CPU, s |
|---|---:|---:|
| baseline | 2.970 | 2.779 |
| candidate | 2.844 | 2.798 |

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 9/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.041 s wall and +0.006 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | -0.366 / -0.306 / -0.117 | -0.365 / -0.090 / +0.021 |
| 2 | 3 | -0.296 / -0.008 / +0.092 | -0.137 / -0.046 / -0.012 |
| 3 | 3 | -0.133 / +0.235 / +0.252 | +0.018 / +0.045 / +0.119 |
| 4 | 3 | -0.074 / +0.022 / +0.535 | -0.079 / +0.155 / +0.418 |
| 5 | 3 | -0.044 / -0.041 / +0.210 | -0.008 / +0.006 / +0.098 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

Unavailable foreign calls and catch_unwind intrinsics are explicit terminal stops. Successful tests avoided those boundaries; their call-site metadata and exact executed bytecode are retained with the command records. Ordinary type and borrow checking remained enabled.

Host build scripts, procedural macros, and their build dependencies use optimization level 0 in every mode. Their first compilation is included in cold command times.

Custom-engine Cargo commands explicitly set `RUSTFLAGS=-Zmir-opt-level=3 -Zinline-mir-threshold=400 -Zinline-mir-hint-threshold=800 -Zinline-mir-forwarder-threshold=240`. Native retains its Cargo development/test profile. Frontend and overflow checks remain enabled. Without an explicit Cargo target these flags can also affect host build tools; exact flags are retained in the command records.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 5.796 | 8.937 | 41.339 |
| baseline | 3.069 | 2.876 | 24.950 |
| candidate | 2.947 | 2.891 | 23.287 |

Native control: `repository`, 18 build jobs, `1` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=18, candidate=18. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 2.807 s wall / 2.591 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 2.319 | 0.136 | 0.006 | 0.010 | 0.005 | 0.006 |
| candidate | 2.269 | 0.127 | 0.005 | 0.010 | 0.004 | 0.006 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 6.119 | 3.118 | 3.130 |
| 2 | 6.374 | 3.172 | 3.184 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.

The candidate enables native Calls/Returns with guest-frame continuations.

The candidate enables persistent full-width native registers.

The baseline enables native Calls/Returns with guest-frame continuations.

The baseline enables persistent full-width native registers.

Custom engines use the shared metadata-only standard library. Its original installation took 10.997 s, including 9.185 s of metadata compilation; that setup is excluded from the command times above. Native uses the installed standard library.
