# Measured inliner public-API protocol

This packet preserves the exact measured driver as probe.rs, SHA-256
e2dda048fadb66456b76ebe9c6a59756c3204e7c76b1bf5ed840a597c6a3996c.
The borrowed public inline_leaves(&Program, LeafInlineOptions) API is called once
per pass process with defaults leaf_operations=192, caller_growth=4096 and
program_growth_percent=50. Its timer includes Program cloning, validation,
analysis, expansion and complete public report construction. The ordinary
exporter uses the private owned route, so this is a component measurement.

Both libraries came from the frozen 231-file source manifests at published base
9e3aaaccddf53d21c448de2ef9ce9a245e5ef6b8. Only inline.rs, inline_graph.rs and
inline_tests.rs differ. Source aggregates and exact per-file/compiler/tool/binary
bindings are in summary.json and the hash-bound raw receipts. Two sequential
private Cargo probe/library builds used pinned nightly-2026-09-08, --release
--locked --offline --jobs 2 and CARGO_INCREMENTAL=0. Registry dependency versions
and checksums were projected from the root lock; no external project/std rebuild.

The exact input is a retained original Fre token-phrase artifact, already exported
and optimized: 28,810,437 bytes, SHA-256
d4e1314465a7bbf8ff8b74caefb1a6dc1ea87a310e6f2c716b02e7b6e5f38096.
It contains 5,421 functions and 1,292,532 operations. The strict decoder checks
version, trailing bytes, input hash and full Program validity. The probe performs
no guest execution. Its preserved absolute paths describe the measured run;
relocating it requires an explicitly recorded source adaptation and new hash.

Executed fixed schedule: two census processes; two initial parity processes;
two warmup pairs in AB then BA order; twenty measured pairs alternating AB/BA
(A=baseline, B=candidate). All 48 processes and both builds completed. Every
process freshly decoded the original input. Parity saved and compared complete
serialized bytecode and the complete public report; all later pass processes
matched both hashes and counts. Timing processes wrote no artifact. No samples
were discarded or retimed. summary.json includes all 48 rows plus all 132 ordinary
export rows, including census/parity/warmup rows rather than only measured pairs.

Actual census: 11,603 direct calls across 4,012 callers, 1,409 functions without a
direct call, and 29 indirect-only callers. The graph scan stayed within limits.
The pass selected 1,783 sites and changed 1,069 callers. Both outputs contained
1,379,627 operations, 30,620,838 bytes, SHA-256
ec7a8841318e01f400b59f57d13949954231cc7be4600e0396304eeca5c3fab9.
The full 673,484-byte report matched at SHA-256
510362b7106c5dc54a8633c0cb2cd743e7ed19619ab5ee620ed4dc9c5aba3657.
This is analysis-and-expansion exposure on post-export data, not an estimate of
original exporter opportunities or an unchanged-artifact pass.

The measured controller was run-screen-wait.py, SHA-256
f2c8038bd09a44bc3d79c12b32c57b02185a1e05c5bd230b0e9b59c2c9752f31.
Its reviewed predecessor 716899881e3b88ab9a62fbee7f9bc0fb7051abd0d38fdc09c94e8e28c37e70d7
was changed only to wait for the shared lock; it did not change samples or flags.
The five-second observer/settlement wrapper was observe-screen.py, SHA-256
0499cf4b32d50bfb6a0ce0f6a6f002aeda8afd6a8e613b957150aa69a631f664.
It sampled free disk for this owned controller and waited its exact child through
completion without signaling any process. Its journal records a clean terminal
exit. Per-child helpers retained fresh 32 GiB disk and 30% memory admission under
the shared benchmark lock. The 3 GiB resource allowance was planning, not a hard
allocation cap. Other full external workloads retained their 50 GiB threshold.
The exact resource/decision plans and observer journal are included or hash-bound.

Parent wait4 supplied whole-process CPU and macOS peak RSS; pass_ns is the driver's
wall timer. Input reading/hash, decode, explicit pre-validation, shape census,
serialization and report hashing are outside pass_ns. Whole-process CPU includes
all those costs and final destruction. The primary aggregation is the geometric
mean of all twenty paired candidate/baseline pass ratios. Process CPU/wall/RSS
and AB/BA strata use geometric means as accepted by root before measurement.

Large public-pass ratio: 0.9636045627916769, with 20/20 candidate wins; AB and BA
ratios are 0.9623342458193636 and 0.9648765566296086. Process CPU/wall/RSS ratios
are 0.9857743012730733, 0.9858483788630147 and 1.0003458713775641. All predeclared
public-pass component thresholds passed.

The separate inline-enabled ordinary exporter panel completed 132 exports across
three fixtures, with 20 measured pairs per fixture and exact artifact/count parity.
Its aggregate CPU ratio was 1.0020233485637626 and wall ratio 0.9990859592171911
(geometric means of case median paired ratios). Nonregression gates passed; the
predeclared whole-export positive endpoint was inconclusive. Thirty focused
release tests and ten native/interpreter/JIT configurations also passed, including
111 seeds per configuration and six expected inhabited-payload rejections among
2,271 children. These facts support only the stated component/adoption evidence.
No full-export improvement, complete Cargo-build speedup, cold-build, runtime or
unknown-holdout improvement is claimed.
