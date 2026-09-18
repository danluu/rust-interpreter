# Skip redundant CFG work during export

The exporter now requests operation totals without retaining per-function CFG reports. In this mode, a function ending in `Return` or `Trap` with no earlier branch or terminal is unchanged by CFG optimization. It keeps its original bytecode and skips reconstruction and both register-initialization analyses. Both whole-program validation passes remain. The existing detailed API still returns its complete report.

## Evidence

Eight focused CFG tests passed, including detailed/summary artifact equality, register-zero reads, interior terminals, and rejection before mutation. Ten fixture/configurations produced identical baseline/candidate bytecode; both VM engines matched native results across 111 seeds each. Three inhabited unsupported cases still rejected in both exporter arms.

A separate diagnostic compared the actual detailed and summary APIs on the same retained, already optimized token-workload program: 5,421 functions and 1,292,532 operations, including 2,682 straight-line functions. The output remained byte-for-byte identical. All 20 measured pairs improved in each metric:

| Metric | Detailed median | Summary median | Geometric mean paired change |
| --- | ---: | ---: | ---: |
| CFG pass wall time | 51.950 ms | 49.143 ms | -5.46% |
| Entire diagnostic CPU | 110.407 ms | 106.034 ms | -4.09% |
| Entire diagnostic wall time | 112.911 ms | 109.153 ms | -3.31% |
| Peak RSS | 171.25 MiB | 166.30 MiB | -2.26% |

The separate ordinary export screen retained 132 exports: two warmups per arm/case and 20 alternating measured pairs for each of three fixtures. Aggregate paired CPU was 0.16% lower and wall time 0.10% lower, with mixed per-case results. **Complete-export improvement is inconclusive.** The measured CFG stage medians fell by 92, 58, and 3 microseconds, but occupied only about 1.08%, 1.30%, and 0.10% of baseline wall time.

The initial complete-export screen did not meet its consistent-gain criterion. Adoption uses the narrower component evidence from the subsequent retained-program diagnostic and the consistently faster fixture CFG stages. This does not establish a full Cargo-build, original pre-CFG workload, unknown-holdout, or runtime speedup.

## Method and provenance

Both exporter builds used the pinned `nightly-2026-09-08-aarch64-apple-darwin` toolchain, offline locked release builds, two build jobs and no incremental compilation. The source base was `987e297af92b9ad48ebb2f8eb5b1e37d73b8f8a2`; only the four recorded CFG source/test files differed. All samples are retained in `summary.json`, including warmups and per-pair values. There was no favorable retiming or outlier exclusion.

The pass diagnostic used one candidate-library binary for both APIs. It performed two artifact-parity runs, four warmup runs and 40 measured runs in alternating order. Each process freshly decoded and validated the fixed input and invoked exactly one public CFG pass. `pass_ns` includes that API's own validations. Process CPU also includes reading, hashing, decoding, serialization and destruction. Peak RSS uses macOS `wait4` bytes.

Input SHA-256: `d4e1314465a7bbf8ff8b74caefb1a6dc1ea87a310e6f2c716b02e7b6e5f38096`, 28,810,437 bytes. Retained provenance: Fre `e0df0b010b156b030a02f073588d28703f4267f3`, token-phrase-allocation; original source SHA-256 `993d76954f4e5f324b137e7d5f9e349dbfb69ef0da9e91ea04ebc9545be3f984`. The input was already exported and optimized, so this is a pass diagnostic rather than the original export pipeline.

`probe.rs` is the exact measured driver. The standalone probe crate retained the root's registry versions/checksums and built only the bytecode library and driver. The first 50 GiB admission attempt launched nothing. A separately recorded bounded-job allowance used a 32 GiB disk reserve and 30% free memory; all launches used fresh checks and the shared benchmark lock. The actual probe build took 11.34 seconds and peaked at 479.25 MiB RSS. No external project or standard library was rebuilt. The complete raw receipts and source/tool hashes remain at the owned paths recorded in `summary.json`.
