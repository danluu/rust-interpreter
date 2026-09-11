# Completed host-object reclamation

Twenty reviewed completed workspace checks released 80,888 non-executable
object-file paths, containing 1,653,205,448 unique inode bytes
(1.54 GiB). All 13,884 other files remain and verify, including test binaries.
All completed qualification records and 2,105 external evidence hashes verify
afterward. Every application finished successfully; no processes were signaled.

One attempted preparation for `native-call-census-02` was rejected because that
diagnostic has no workspace-check status receipt. It created no inventory and
changed no target. The separately reviewed twenty inventories were unaffected.

Observed free space afterward was 20.650 GiB. The
three preceding completed one-cycle cold histories each retained 11.305 GiB of
unique cache contents. This is near the approximate 21 GiB planning target and
leaves about 9.3 GiB beyond those known contents. The next history retains the
existing eight-GiB per-command guard; shared-host space is not reserved.
These are resource observations outside benchmark timing, not performance gains.

See [review](inventory-review.json), [verification](summary.json) and
[qualified object reclamation](../workspace-object-reclaim-checks-01/summary.json).
