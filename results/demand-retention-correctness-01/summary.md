# Demand-retention correctness

The final debug qualification passed **126 tests**: 94 Rust tests, 7 retention
launcher tests, 6 direct compiler histories, 1 Cargo history, and 18 existing
borrow-check compatibility tests. The final source hashes match implementation
commit `355f12ad83f1140625482f526e2541ac7ce92f4e` and remained unchanged during the run.
All builds and real compiler tests held the shared repository benchmark lock.

The original fixture attempt is retained as a failure: six real test functions
reported 15 failed subcases because an incorrect save-provider address comparison
rejected enabled compilations before analysis. That pre-fix uncommitted source is
identified by hashes; its full old source text was not retained. The corrected
intermediate run passed 107 tests, and the later expanded run passed 126.

The histories cover full type and borrow checking, errors in uncalled bodies,
warnings and lint expectations, failed-edit restoration, newly reachable generic
and opaque results, namespace transitions, statics/TLS/link attributes, hard-link
preservation, Cargo host build scripts and dependency edits, native outputs,
export byte parity and execution with the retained VM. Exact commands, receipts,
logs and available source-state records are in `evidence.tar.gz`; its internal
`MANIFEST.json` hashes every retained member. `summary.json` hashes each stage log.

Every observed successful retention save used one serialization pass and started
zero serializer query jobs. The retry path has pinned-source review but **no
positive runtime regression case** yet. These are correctness results; they make
**no performance claim and do not establish the 0.5-second target**. Matched-profile
release qualification is recorded in `../demand-retention-release-02`.
