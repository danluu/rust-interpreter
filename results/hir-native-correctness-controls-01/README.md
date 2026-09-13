# Native correctness driver source controls

All six Python controls passed with no skips at source `8b83ddd7`. They cover all 26 required ReadyHit unit names, immutable checkpoint identity, reviewed plan and fixed commands/capacity, visible verified native hits with split no-capture test output, the exact option test, separate predecessor archives, and missing/tampered history rejection. These are source-contract controls; no compiler build or native test ran as part of this six-test command.

The archive retains exact raw stdout/stderr, command environment and process receipts, the outer test supervisor, and all 20 original frozen inputs (including imported HIRC inputs). Every member was read back and hash verified, and all sources were rechecked. Native/compiler sources, plans, targets, and caches were unchanged.

Archive attempt 01 exhausted its 600-second lock admission before reading evidence. Attempt 02 failed to start its helper after a local preparation syntax error; it read no evidence. Both failures remain in the successful attempt 03 archive. Attempt 03 contains 41 verified members (120,415 compressed bytes), SHA256 `f994d94261bdc123f197ed9553f13962ba760fccc45733e5a9391f8ed96c48a1`; its completed supervisor and helper receipts are retained separately in `archive-process/`.

The later native compiler sequence is a separate failed qualification. Its missing capture records and the subsequent correction are not covered by these six Python test results.
