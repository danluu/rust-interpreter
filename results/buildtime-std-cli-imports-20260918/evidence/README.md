# Skip unselected installer imports in standalone std setup

Conditionally importing the selected compiler and Cargo helpers reduced CPU in the measured standalone std_mir import/main component by **3.88%**, with **18/20 paired wins**. Median component CPU was **16.1465 → 15.5575 ms**; the median paired saving was **0.6255 ms**. All **eight predeclared gates** passed. This is evidence for the tested standalone stock ready-reuse route, not an interpreter-launcher, full-build, compiler/export or unknown-holdout speedup.

| Metric | Geometric mean candidate/baseline | Median paired saving |
|---|---:|---:|
| Component CPU | 0.961175 | 0.6255 ms |
| Component wall | 0.960817 | 0.6240 ms |
| Complete driver CPU | 0.981115 | 0.6520 ms |
| Complete driver wall | 0.979690 | 0.7447 ms |
| Complete driver peak RSS | 0.993787 | 155,648 bytes |

Ratios are geometric means of the twenty unrounded paired ratios. The complete instrumented driver used about 1.89% less CPU and 2.03% less wall time in this screen. Those observations include harness work and do not establish general startup or setup acceleration. The immutable decision required component CPU ≤ 0.98, at least 15 strict wins, both order strata below 1, component wall ≤ 1, and complete-driver CPU/wall/RSS guards ≤ 1.01/1.02/1.05.

The production change moves only two imports under their corresponding selection checks in standalone std_mir.main. Selected-tool loading, argument forwarding, exceptions and setup remain on the existing route. Source inverse comparison preserves every other production byte. Eight new CLI semantic tests and thirteen unchanged custom compiler/Cargo tests passed on the candidate, with no skips. These twenty-one tests are candidate-only; the new import-boundary tests are not represented as baseline success tests.

Each fresh driver timed actual std_mir import through actual main return. A common wrapper installed after the timed import imports real toolchain_lookup inside the clock, temporarily stubs only compiler_identity to an exact argument-checked synthetic result, delegates to real checked_std_mir, and restores the function. Both arms therefore pay real lookup/tempfile imports. Actual cache identity, corpus/source-lock hashing, ready ownership and std_mir_readmission.validate execute. No compiler query, Cargo, std compilation, guest, or native code generation ran.

Both arms used the same absolute prepared fixture: 26 deterministic 1 KiB regular files with a retained ready manifest's metadata name shape. These are synthetic bytes, not valid Rust metadata. The full 47-entry / 36,370-byte fixture state is retained, including corpus, synthetic source Cargo.lock, ready identity and the precreated writable std lock. Preparation read source constants without importing or calling project APIs; actual main parity occurred in the fixed screen. Existing real metadata payloads were neither read nor copied.

The fixed panel contains two parity processes, four AB/BA warmups and forty measured processes forming twenty balanced AB/BA pairs. Each driver has a separate memory admission receipt:46 reports and92 settled direct children, all retained. Pinned CPython 3.14.7 used a new common private bytecode prefix. Only warmups could write bytecode; measured processes used -B with the frozen 72-file / 1,843,874-byte cache and 101 dependency-file proofs. Imports and main stay inside the component clock; driver configuration reading, validation and reporting outside that clock remain included in its outer wait4 CPU/wall/RSS measurements, while parent binding, cache and fixture checks are outside both clocks.

The process-denying audit hook and common wrapper remain inside the component clock. Audit-hook overhead depends on the events produced by the import graph, so these measurements cannot separate all instrumentation cost from the imports removed. Source-tree path lengths and fresh-process scheduling are also properties of this controlled experiment. No uninstrumented or general holdout performance claim is made.

The root and independent audits checked the fixed schedule, all 92 settlements / 184 logs, 100 paired ratios / eight gates, 2,448 source/runtime bindings, bytecode/dependency correspondence and the complete fixture. summary.json preserves the original unrounded summary and gate values. Packaging separately recomputed all raw paired ratios and medians and checked aggregates to 1e-14 using system Python; it did not rerun an API or workload.

## Evidence and reproduction

raw/all-stage-files.jsonl.gz losslessly contains every original file from unit-screen-01, fixture-preparation-01 and screen-01. Every path has its own full data_base64 payload plus raw size, SHA256 and original stamp. Decode each payload independently and verify its raw_bytes/raw_sha256. raw/file-index.json.gz supplies the same index without payloads, plus original directory identities. Direct raw/<stage>/result.json.gz files restore the exact original result bytes.

artifact-manifest.json records every stored file's raw/stored byte lengths and hashes, and its absolute original path or generated inputs; it alone excludes itself. Gzip uses level 9, mtime 0 and no embedded filename. Every archived file was decoded and compared byte-for-byte with its original during packaging. All raw stages and measured trees remain untouched.

The bundle includes the exact source delta, executed semantic-test sources, full source/runtime inventories, reviewed controls, frozen decision and descriptors, all prerequisite results and audits, complete private cache files, and preserved pre-data drafts. The retained assembly refusal was a source-only comparison of integer versus string timestamps before any output; the corrected cross-check retained exact unit-schema runtime links. No timing sample was retried, excluded or replaced.

Historical absolute paths are provenance, not reusable output destinations. Reproduction requires a reviewed rebind to fresh owned outputs and equivalent pinned runtimes, with new receipts under the frozen protocol. Never overwrite retained evidence. Source integration against the later publication base is separately recorded; the parent owns committing and publishing.

Packaging only read, hashed, copied and compressed existing evidence. No tests, compiler/native queries, measured APIs or benchmarks were rerun.
