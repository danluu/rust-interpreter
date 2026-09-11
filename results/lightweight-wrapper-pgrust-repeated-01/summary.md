# Production edits and existing pgrust tests

Generalize a public byte-hash input to borrowed AsRef containers. Existing array and slice callers can instantiate different generic ABIs; all four original hashfn tests remain unchanged..

1 cumulative production-body refactors across 15 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 15/15 complete-command pairs. The median paired candidate-minus-baseline difference is -0.023 s wall and -0.022 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 15 | -0.030 / -0.023 / -0.005 | -0.029 / -0.022 / -0.005 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.664 | 0.634 | 0.993 |
| baseline | 0.499 | 0.490 | 0.501 |
| candidate | 0.479 | 0.470 | 0.489 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom commands use 4 build jobs. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.390 s wall / 0.384 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.016 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 |
| candidate | 0.016 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 0.654 | 0.495 | 0.477 |
| 2 | 0.718 | 0.498 | 0.480 |
| 3 | 0.654 | 0.500 | 0.481 |
| 4 | 0.691 | 0.495 | 0.479 |
| 5 | 0.658 | 0.500 | 0.480 |
| 6 | 0.652 | 0.493 | 0.480 |
| 7 | 0.652 | 0.500 | 0.469 |
| 8 | 0.665 | 0.497 | 0.480 |
| 9 | 0.723 | 0.490 | 0.486 |
| 10 | 0.751 | 0.509 | 0.480 |
| 11 | 0.644 | 0.492 | 0.477 |
| 12 | 0.657 | 0.501 | 0.474 |
| 13 | 0.658 | 0.503 | 0.474 |
| 14 | 0.659 | 0.507 | 0.470 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 15 edited samples per mode on a shared host do not establish a whole-suite or general performance result.
