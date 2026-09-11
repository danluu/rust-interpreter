# Interrupted batch, verified completed prefix

Five archives completed and verified before the sixth child failed to acquire
`.work/benchmark.lock`. The root agent incorrectly queued its pgrust receipt
verifier before the batch finished. That verifier acquired the lock between
children; the coordinator uses a nonblocking lock and exited before applying
cache six. No unrelated process was controlled.

The original supervisor ended with code 1. All five completed targets have
matching reviewed inventories, final receipts, archive sizes, empty retired
roots and 33 unchanged external evidence hashes. They preserve 55,907 file
paths and 15,504,417,461 unique original bytes in 5,197,819,720 archive bytes.
This is a verified prefix, not a completed eight-target batch.

The remaining three status files are byte-identical to their prepared state;
no partial archive or result exists. A separate lock-held audit rechecked their
entire inventories, closed files, exact corpus ownership and external proofs.
The [reviewed remainder](../warm-storage-batch-01-recovery-01/inventory-review.json)
uses the same archive IDs and unchanged plans, with a new three-entry batch.
Do not retry the original eight-entry batch or queue another lock waiter while
any archive batch is active. The [recovery completed](../warm-storage-batch-01-recovery-01/assessment.md);
[combined evidence](recovery-summary.json) accounts for all eight reviewed targets.

[Verified prefix](partial-summary.json), [original review](inventory-review.json).
