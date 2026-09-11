# Production edits and existing pgrust tests

Generalize a public byte-hash input to borrowed AsRef containers. Existing array and slice callers can instantiate different generic ABIs; all four original hashfn tests remain unchanged..

1 cumulative production-body refactors across 3 cycle(s); test source is unchanged. Each cycle builds the original source, rejects a wrong production edit in every mode, then applies the refactors. Only the first original build is cold; subsequent anchors are recorded separately. Every edited sample changes the source that its mode last built. Full subprocess time includes Cargo, launcher, compilation, and execution. Native runs the selected tests in one command. Custom engines use one command.

Baseline and candidate use `jit` with separate Cargo caches. The installed builds are pinned by their recorded keys and binary hashes; source edits and selected tests match within every pair. Each executed artifact is retained. Snapshot copying occurs after the command timer; artifact hashing inside the launcher is timed and recorded.

The candidate wins 0/3 complete-command pairs. The median paired candidate-minus-baseline difference is +0.003 s wall and +0.002 s child CPU. Bytecode equality is required and verified. Per-edit Cargo and execution stages are retained in JSON.

| Edit | Repeats | Paired wall change min / median / max, s | Paired CPU change min / median / max, s |
|---|---:|---:|---:|
| 1 | 3 | +0.000 / +0.003 / +0.003 | +0.000 / +0.002 / +0.003 |

This is descriptive spread within each actual edit, not a confidence interval. Cycles share caches and host conditions.

| Mode | Median edited wall seconds | Median edited child CPU seconds | Cold wall seconds |
|---|---:|---:|---:|
| native | 0.648 | 0.633 | 1.087 |
| baseline | 0.494 | 0.484 | 0.520 |
| candidate | 0.497 | 0.487 | 0.924 |

Native control: `o0-incremental`, 18 build jobs, `default` test threads, explicit rustc arguments `[]`. Custom build jobs: baseline=4, candidate=18. This labels the configuration; it does not establish the fastest native control.

Independent Cargo-check reference: 0.385 s wall / 0.379 s child CPU, median after edits. It executes no tests and runs after each primary triplet in a separate target directory. It is not a strict lower bound, and subtracting it does not isolate exporter cost.

Exporter timing scopes (medians, seconds; pass times are nested within lowering/export and must not be added to it):

| Mode | Frontend | Lowering/export | Scalar frames | Promotion | Inlining | CFG |
|---|---:|---:|---:|---:|---:|---:|
| baseline | 0.016 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 |
| candidate | 0.016 | 0.007 | 0.000 | 0.000 | 0.000 | 0.000 |

| Anchor cycle (zero-based) | native | baseline | candidate |
|---|:---:|:---:|:---:|
| 1 | 0.644 | 0.496 | 0.499 |
| 2 | 0.687 | 0.491 | 0.495 |

CPU time sums user and system time for each waited-for child tree, including its completed descendants and excluding the harness itself. Commands run serially within the harness, so unrelated processes do not enter that accounting.

Cold means empty per-engine artifact caches; tool bootstrap, installed sysroot, downloads, and OS file-cache coldness are excluded. 3 edited samples per mode on a shared host do not establish a whole-suite or general performance result.
