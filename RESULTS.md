# Earlier native-cache and Cargo publication measurements

The subsequent custom interpreter implementation, actual-edit benchmarks, and
checking-policy comparisons are in [INTERPRETER.md](INTERPRETER.md). This page
records the earlier native experiment; its unchanged-build result does not
establish a benefit for ordinary edits.

This phase produced a working native compiler/cache experiment, a five-project benchmark harness, and a macOS Cargo publication fix. **The function cache did not solve ordinary warm body edits.** Its measured win was preserving an unchanged executable across Cargo commands; this avoided paying a large launch cost again on this host.

All measurements below are local observations on a shared Apple M5 Max (18 logical CPUs, 48 GiB RAM). Sources and compiler are pinned. Cold builds have one observation per condition; warm medians have five observations unless stated otherwise. No confidence interval or production-readiness claim is made.

## The implemented improvement: unchanged build/run loops

A controlled diagnostic found that a no-op Cargo build replaced the public executable with a new inode even though no compiler artifacts rebuilt. The following pgrust launch took seconds; another direct launch took about 10 ms. Running the ordinary `--version` command first showed the same delay, and `cargo run` reproduced it. The delay was not specific to the synthetic edit probe. The exact OS subsystem responsible remains unproven. [Diagnostic records](results/dev-profiles-03/startup-diagnostic.json).

The Cargo change keeps the existing destination only after a complete byte comparison. It conservatively declines reuse for symlinks, non-executables, differing ownership/permissions/flags, extended attributes, changed files, and I/O errors. Changed output follows normal publication. It neither installs a daemon nor keeps application state alive. Cargo already documents its macOS file-copy path and an earlier hard-link race. [Pinned Cargo source](https://github.com/rust-lang/cargo/blob/3c0b534756e166d12eb9fd2e1abfe5b42ac6101e/crates/cargo-util/src/paths.rs#L606).

The following comparison uses the **same locally built Cargo binary** with the flag off/on, alternating order, three samples per condition, and zero rebuilt artifacts. Times include Cargo, the edit-validation launch, and a small project workload. Python launcher overhead is excluded.

| Project, LLVM | Control | Preserve executable | Ratio |
|---|---:|---:|---:|
| rg-aot | 0.273 s | 0.075 s | 3.6x |
| fre | 0.342 s | 0.104 s | 3.3x |
| pgrust | 3.660 s | 0.621 s | 5.9x |
| ruff | 1.268 s | 0.216 s | 5.9x |
| nushell | 4.958 s | 0.387 s | 12.8x |

**These are unchanged-code results, not speedups for newly edited bodies.** The implementation is available through `scripts/dev.py --preserve-executables`; it uses a separate Cargo build and retains the normal LLVM/panic policy by default. [Setup and use](README.md), [all publication measurements](results/dev-profiles-03/publication-summary.md).

## Backend experiment: cold gains do not establish warm gains

Each cell is **cold / warm body-edit build seconds**. These matched controls use repository optimization/debug settings, incremental compilation enabled, and `panic=abort`. Each body edit uses a new immediate value; the resulting program must produce the expected result. There were 255 accepted build/edit/revert/no-op samples and no failed configurations in this pass.

| Project | LLVM | Cranelift | Cached Cranelift |
|---|---:|---:|---:|
| rg-aot | 3.600 / 0.199 | 3.513 / 0.203 | 3.730 / 0.198 |
| fre | 8.934 / 1.224 | 8.073 / 1.211 | 9.563 / 1.220 |
| pgrust | 106.581 / 1.677 | 95.599 / 1.573 | 105.975 / 1.438 |
| ruff | 70.757 / 0.483 | 44.818 / 0.705 | 50.522 / 0.715 |
| nushell | 90.974 / 1.182 | 73.989 / 1.355 | 79.660 / 1.174 |

The cache preserves Cranelift function stencils across compiler processes, with integrity checks and atomic publication. Rustc still performs type checking, borrow checking, and constant evaluation. Existing Cargo/rustc incrementality already removed most native work for these edits: cache-enabled warm edits examined only 8 functions in rg-aot, 10 in pgrust, 41 in Ruff, 23 in Nushell, and 238 in fre. Avoiding generation of those functions did not consistently reduce the whole build. Cache hit rate is not a useful adoption criterion by itself. [Complete build and feedback results](results/dev-profiles-03/summary.md).

**pgrust profile qualification:** its repository disables incremental compilation. A separate 22-sample LLVM pass retained that setting and ordinary unwinding: cold build 88.183 s, warm body-edit median 1.201 s (three edits). Its matched abort-mode control was 81.138 s cold and 1.752 s warm. These are a separate, noisy run; do not attribute the difference from the main matrix to one isolated factor. They demonstrate why the forced-incremental matrix is not a stock pgrust baseline. The launcher preserves repository profiles. [Native repository-profile results](results/native-repository-04/summary.md).

## Execution cost also depends on the workload

Five alternating measured executions per backend, following an unmeasured warm-up. Output checks passed for all 60 observations. These are bounded development-profile workloads, not full application suites.

| Workload | LLVM | Cranelift | Cached Cranelift |
|---|---:|---:|---:|
| rg-aot | 3.215 s | 2.898 s | 2.889 s |
| fre | 0.192 s | 0.304 s | 0.306 s |
| ruff | 0.022 s | 0.093 s | 0.094 s |
| nushell | 0.188 s | 0.182 s | 0.182 s |

rg-aot scans a generated corpus with three queries; fre repeatedly searches a checked haystack; Ruff checks seeded diagnostics in 2,000 functions; Nushell executes an arithmetic pipeline. Cranelift helped some workloads and hurt others. pgrust has compile/link/startup coverage only, not database execution coverage. [Runtime aggregates](results/dev-profiles-03/runtime-summary.json).

## Other findings and implementation limits

- The first exploratory run used `debug=0`, which also enabled post-link debug stripping on this Cargo version. On macOS this introduced an extra rewrite of large binaries. An instrumented pgrust Cranelift final-crate link phase was 1.336 s with stripping and 0.560 s with `strip=none`; the linker subprocess itself was 0.594/0.527 s. These are diagnostic observations, with nested phases and additional Cargo rebuilds, not warm-matrix samples. The main matrix therefore retains repository debug settings. [Phase records](results/pilot-02/link-diagnostics.json), [Cargo explanation of the stripping default](https://blog.rust-lang.org/inside-rust/2024/02/13/this-development-cycle-in-cargo-1-77/).
- Bundled LLD was slower than the system linker for the tested large macOS binaries. It remains an explicit experiment, not a default.
- fre is exercised through an independent consumer of its library. An in-workspace example hit an existing unrelated dev-dependency build error; that failure is retained in the exploratory logs, and fre itself was not patched.
- Cranelift fast modes require explicit panic-abort semantics here. Ordinary tests and release builds use LLVM. pgrust depends on unwinding, so successful abort-mode startup does not qualify its database behavior.
- This native experiment had no JIT, interpreter tier, compiler daemon, hot reload, global cache eviction, or representative developer edit-history replay. Most measured edits were entry-point bodies. The subsequent interpreter is documented separately; public API/trait changes, macro/build-script invalidation, full debug/unwind compatibility, memory ceilings, and other platforms remain qualification work.

## Validation and next implementation decisions

Passed checks include storage corruption/restart/concurrent-publication tests; LLVM-vs-cached-Cranelift execution across callee, layout, constant, and source-location changes; Cranelift recompilation verification of cache hits; rejection of invalid uncalled bodies and bad constants; six launcher combinations preserving Cargo flags, host unwinding, and application arguments; nine publication integration cases; and eight native rg-aot tests. The pinned Cranelift LLVM-IR dump path has an upstream limitation that is recorded, rather than counted as supported.

A separate Cranelift build with its experimental unwinding feature failed to compile the unwind fixture in both cache modes: the exception-table section was invalid for Mach-O. LLVM compiled and ran it successfully. This is a recorded compatibility failure, not a passing test or an enabled launcher feature. [Validation results](results/validation-summary.json).

An additional matched experiment measured the launcher against its exact resolved Cargo command on the tiny integration fixture. Median added time was 48 ms for LLVM and 102–105 ms for the Cranelift modes, with every measured artifact fresh. This exceeds the proposed small no-op overhead gate against the improved direct-Cargo baseline. Use the documented direct Cargo command when that overhead matters; the wrapper remains a convenience prototype. [Launcher measurements](results/launcher-overhead.json).

1. Keep the proven publication optimization separate and opt-in while extending its platform and Cargo integration coverage. Reduce the measured launcher overhead and repeat the comparison on the full corpus before declaring its overhead gate passed.
2. Keep LLVM as the general default. The function-cache feasibility experiment failed the warm-benefit gate; do not add more cache layers merely to increase hit counts.
3. Add recorded developer edits and broader invalidation cases, with ordinary panic behavior and actual test workloads. Retain each project's native settings and compare candidate policies against that baseline.
4. For body edits, investigate the remaining link/publication/first-execution costs and frontend costs separately. A native materialization experiment must include relocations, initialization, debug information, unwinding, and fresh-process semantics. Only add demand code generation or an interpreter after demonstrating that it saves the measured residual work.

This is evidence from this implementation and host, not a diagnosis of the colleague's unpublished interpreter. The original staged design and five rounds of persona reviews remain in [PLAN.md](PLAN.md) and [persona-reviews.md](persona-reviews.md). Private source and detailed compiler logs remain under ignored `.work/`.
