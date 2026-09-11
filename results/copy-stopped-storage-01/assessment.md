# Stopped Nushell caches archived without changing the benchmark result

All four reviewed targets complete and verify: 41,026 paths, 10,620,219,865
original payload bytes and 3,438,584,679 archive bytes. Every payload was decoded
and hashed before its original cache path was retired. All 46 distinct evidence
hashes remain unchanged, including the original stopped receipts, source history
and four executed bytecode snapshots. Source restoration still verifies.

The separate `stopped-workflow` proof preserves zero completed workflows and
zero successful-edit pairs. It does not convert the interrupted benchmark into
a successful run. No private target or unrelated process was modified.

The [reviewed inventory](inventory-review.json) was committed as `5c6ebf9` before
application. The [final receipt](summary.json) binds all four exact archives and
the qualified tools. This is storage maintenance outside benchmark timers.

The [new admission check](../copy-heldout-retry-space-01/assessment.md) still
requires additional space before a fresh Nushell history can start.
