# Ruff HIR body-cache self-profile diagnostic

The cache-on route remains slower in this single instrumented edited-compiler comparison. The largest positive observed phase difference is incremental session-directory preparation: **0.000954 s off versus 0.383906 s on**. The selected compiler reports **3 versus 1,414 files hard-linked**, respectively. This points to per-body sidecar storage as a candidate for further work; it does not measure the benefit of a packed format.

| Selected edited compiler observation | Cache off | Capture + reuse on |
| --- | ---: | ---: |
| Actual compiler elapsed time | 3.423786 s | 3.635066 s |
| Recorded thread-span total | 3.376634 s | 3.589623 s |
| Session-directory preparation self time | 0.000954 s | 0.383906 s |
| `lower_to_hir` self time | 0.295638 s | 0.467368 s |
| `expand_proc_macro` self time | 0.546403 s | 0.524015 s |
| Proc-macro invocation count | 2,396 | 2,396 |
| Direct selected HIR cache hits | 0 | 1,411 |
| Direct selected HIR captures | 0 | 0 |

Each mode starts with a fresh Cargo metadata target, runs the unchanged six existing Ruff registry tests, applies the same first production edit once, and restores the original source. All six suites passed; off/on bytecode matched in all three source states. Every call report has zero unavailable call sites, but the diagnostic still enables `trap-unsupported-calls`; strict readiness and the 0.5 s target remain unqualified. All 11,119 source files (89,102,713 bytes) were restored and independently rehashed.

The history deliberately preserves two failed attempts. Attempt 01 failed before workload admission on a Path/str helper mismatch, with zero workload children. Attempt 02 completed both primes and the candidate edited compilation, then rejected its 172,033,161-byte profile against the original 128 MiB retention bound. A distinct reviewed continuation retained that completed compiler result, ran its test suite, and executed only the nine remaining commands with an explicit 256 MiB file/512 MiB combined profile bound. It did not repeat either prime or the candidate edited compilation. The archive contains all 14 actual direct child receipts, 650 wrapper records, both complete binary self-profiles, exact compiler argv/direct stderr, source freezes, raw outputs, artifacts, suites, and the qualified reader's JSON summaries.

This is one continued diagnostic pair, with the candidate measured before the retention failure and the baseline later. It is not a balanced latency distribution. Recorded thread spans are not CPU time; inclusive query times overlap. `lower_to_hir` includes stock lowering and cache work, with no dedicated body-cache subspans to isolate option hashing, traversal, or validation. Exporter “lowering” is separately defined as MIR-to-bytecode export/publication. Direct compiler stderr avoids Cargo's replay of cached dependency diagnostics. The observed 1,411 hits do not provide a denominator for silently rejected or unsupported bodies.

`summary.json` contains the selected observations and scope; `manifest.json` maps every retained source path to exact bytes. `evidence.tar.gz` has 1,894 logical members, deduplicated with backward tar hard links to 1,531 physical members. Complete member hashes and gzip EOF/CRC were independently verified. `archive-execution.json` retains the outer launch, supervisor, terminal and independent readback evidence. Mutable Cargo target caches are excluded; complete profiles and result artifacts are included.
