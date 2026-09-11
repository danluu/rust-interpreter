# Completed storage batch for the next cold history

All 24 reviewed targets completed and verify: 64,858 paths and
18,002,014,724 unique bytes (16.77 GiB) preserved in
6,123,737,861 archive bytes (5.70 GiB).
Every payload was decoded and hashed before retirement. All terminal receipts,
reviewed targets, provenance kinds, reservations, empty roots, archive sizes and
2,150 distinct external evidence hashes verify.

The batch includes the first fixed worker cold history's four Cargo targets and
twenty completed unpublished debug-check caches. Historical source snapshots,
test logs, bytecode captures and installed tools remain outside these retired
targets. This brings archives to 81: sixty workflow targets and 21 host targets.
The host reported about 23 GiB available afterward; shared-volume free space
is an observation, not an exact measure of bytes physically reclaimed.

Preparation supervisor 71493/controller 71505, review 85367/85377, application
9570/9580 and assessment 20207/20213 all finished successfully. No other lock
waiter or benchmark was launched during the application batch.

See [review](inventory-review.json), [terminal assessment](summary.json) and
[host-selector qualification](../host-cache-selector-03/assessment.md).
