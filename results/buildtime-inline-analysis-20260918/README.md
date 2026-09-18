# Reuse inliner analysis during export

Leaf inlining now reuses the bounded call-graph scan to skip call-site analysis for functions without direct calls. It rejects oversized leaves before scanning their bodies and combines return, opcode and call-count eligibility into one scan. Selection, growth budgets, register proofs, validation and complete public reports remain unchanged. Graph-limit fallbacks conservatively retain caller analysis.

## Evidence

All 30 focused inliner, whole-call and graph tests passed. Ten fixture/configurations with inlining enabled produced identical baseline/candidate bytecode and inline counts; both VM engines matched native results across 111 inputs each. Three inhabited unsupported payloads still rejected in both exporter arms.

A retained token-workload program contained 5,421 functions and 1,292,532 operations. Of these functions, 1,409 had no direct calls and 1,274 exceeded the leaf operation limit. Both implementations selected the same 1,783 inline sites, changed 1,069 callers and produced byte-for-byte identical programs and complete reports.

| Metric | Baseline median | Candidate median | Geometric mean paired change |
| --- | ---: | ---: | ---: |
| Public inlining pass wall time | 58.349 ms | 56.286 ms | -3.64% |
| Entire diagnostic CPU | 124.442 ms | 122.136 ms | -1.42% |
| Entire diagnostic wall time | 128.033 ms | 125.886 ms | -1.42% |
| Peak RSS | 268.99 MiB | 269.13 MiB | +0.03% |

All 20 measured pass pairs improved; 19/20 improved in process CPU and wall time. Both execution-order strata improved in pass time. The result passed the component thresholds recorded before measurement.

The separate ordinary screen retained 132 inline-enabled exports across three fixtures. Aggregate paired CPU was 0.20% higher and wall time 0.09% lower. **Complete-export improvement is inconclusive.** All predefined ordinary-export regression checks passed. Adoption follows the predeclared component route; these results do not establish a full Cargo-build or unknown-holdout speedup.

## Method and limits

The common source base was `9e3aaaccddf53d21c448de2ef9ce9a245e5ef6b8`. Only `inline.rs`, `inline_graph.rs` and `inline_tests.rs` differed. Builds used the pinned `nightly-2026-09-08-aarch64-apple-darwin` toolchain, locked offline dependencies, two jobs and no incremental compilation.

The large diagnostic used separate baseline/candidate libraries with identical drivers. It ran two census processes, two complete artifact/report comparisons, two warmup pairs and 20 measured pairs in alternating order. Every sample is retained in `summary.json`; none was discarded or retimed.

`probe.rs` calls the actual borrowed public API once. Its pass clock includes validation, analysis, report construction and cloning the original program. The exporter uses an owned API, so this diagnostic is not its exact pipeline. Whole-process metrics also include reading, decoding, hashing, serialization and destruction. Peak RSS is macOS `wait4` bytes.

The input was already exported and optimized: SHA-256 `d4e1314465a7bbf8ff8b74caefb1a6dc1ea87a310e6f2c716b02e7b6e5f38096`, 28,810,437 bytes. Retained provenance is Fre `e0df0b010b156b030a02f073588d28703f4267f3`, token-phrase-allocation. Its census describes this retained program, not the original pre-inline exporter input.

All workloads used the shared benchmark lock and fresh disk/memory admission. The bounded local-job reserve was 32 GiB and 30% free memory; a parent observer recorded disk space every five seconds during the probe controller and waited for its exact child. Full protocols, thresholds, source/tool identities, raw receipt paths and hashes are recorded alongside the measurements.
