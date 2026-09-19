# Reuse the file stat during std metadata validation

Using one file stat reduced CPU in the measured public validation component by **23.25% for matching saved stamps** and **13.94% for an existing readmission receipt**. Each route had **20/20 paired CPU wins**, and all **16 predeclared gates** passed. This supports the two reused metadata-validation routes; it does not establish a whole setup, build, exporter or unknown-holdout speedup.

| Actual validate route | Component CPU reduction | Median component CPU, µs | Median paired CPU saving, µs | Process CPU C/B | Process wall C/B |
|---|---:|---:|---:|---:|---:|
| Matching saved stamps | 23.25% | 139.0 → 104.5 | 32.5 | 1.004386 | 1.004772 |
| Existing readmission receipt | 13.94% | 221.0 → 186.5 | 32.0 | 0.999595 | 1.001871 |

Reductions use each route's geometric mean of paired candidate/baseline CPU ratios. Both saved about 32 microseconds per call. Whole-driver CPU increased 0.44% for matching stamps and decreased 0.04% for receipt reuse; whole-driver wall increased 0.48% and 0.19%. These remained inside the fixed 1% CPU and 2% wall guards. RSS guards passed. These whole-driver results do not support a claim of overall startup acceleration.

The production change reuses a successful stat result for the regular-file test and saved identity. It is enabled only on CPython 3.14 POSIX, whose Path.is_file error policy is explicitly qualified. Other runtimes retain the original path. Every downstream content hash, opened-file identity check, receipt check and final validation remains. Stable path/error behavior is covered; the proposal does not claim identical observations when another process mutates a path between the original two syscalls.

Both arms used the same absolute owned fixtures. Each of two trees has 26 deterministic 1 KiB regular files with the path layout and insertion order of a retained ready manifest. These are synthetic payloads, not valid Rust metadata. No original 112,958,025-byte metadata payload was read or copied. Actual baseline validate was called once on matching saved stamps and twice on the other tree to create and reuse the exact receipt. The complete 68-entry, 76,962-byte frozen fixture state is retained.

The screen kept four parity, eight warmup and eighty measured calls: 20 balanced AB/BA pairs per route, plus 92 separate memory checks. All 92 API reports and 184 child settlements are included. Each fresh driver called the actual public API once. Imports, source proofs, manifest parsing and complete fixture snapshots are outside the component clock but inside whole-process wait4 measurements. Only warmups populate the private bytecode cache; measured calls read the frozen 30 files / 620,235 bytes with -B.

Correctness passed the same twelve semantic tests against both implementations on CPython 3.14.7 and actual CPython 3.9.6: 48 executions, no skips. The candidate guard was true on 3.14 and false on 3.9. Tests cover complete-hash readmission, receipt reuse and corruption, file types and followed symlinks, mutation during hashing, native error policy, transient faults, and validation precedence.

All source refinements happened before C9 execution. Initial v1 retry handling was rejected during source review because a transient error could be hidden by the retry. V2 introduced the conservative runtime guard and never retries the initial failure. V3 changed only the two new fault tests so they inject the same failure through both os.stat and Python 3.9's cached pathlib accessor. Production v2/v3 bytes are identical; existing seven test methods, all twelve final names and every performance gate stayed fixed. The exact proposals and preserved controller/plan corrections are included.

The root and independent audits checked the complete fixed schedule, every settlement/log, all 200 raw paired ratios, all 16 gates, 487 source bindings, full fixtures and warm cache/dependency correspondence. The independent audit exactly reproduced aggregates under the pinned Python 3.14. Packaging separately reproduced all raw ratios and checked aggregates to 1e-14 using system Python; summary.json preserves the original unrounded values exactly.

## Evidence and reproduction

summary.json keeps the complete original timing.summary and timing.gates members without pooling unlike routes. The direct raw result gzip files restore exact original bytes. raw/all-stage-files.jsonl.gz losslessly contains all 1,467 files from the four completed stages, including each planned/start/terminal record, config, API report, stdout/stderr file, resource observation, cache file, dependency proof, fixture and raw audit. Decode each record's data_base64 and verify its raw_bytes and raw_sha256. raw/file-index.json.gz provides the same file identities and original directory records without payloads.

artifact-manifest.json maps every stored file to its absolute original path or generated inputs, raw size/hash and stored size/hash; only the manifest excludes itself. Compression is gzip level 9 with mtime 0 and no embedded filename. Every archive record was decoded and compared byte-for-byte to its original during packaging. The original evidence and measured worktrees remain untouched.

Source copies, exact patches, decision, controllers, drivers, input descriptors, correctness/fixture evidence and both independent audit notes are included. Historical absolute paths are provenance, not reusable output destinations. Reproduction requires a reviewed rebind to fresh owned paths/fixtures, equivalent pinned runtimes and new receipts under the frozen protocol. No original evidence should be overwritten.

Packaging only read, hashed, copied and compressed existing evidence. No tests, target API calls, compiler queries or timing samples were rerun. Publication is handled separately by the parent.
