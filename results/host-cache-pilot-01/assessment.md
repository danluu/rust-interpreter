# Completed-debug archive pilot

The actual batch preparation, application and terminal assessor all pass.
The completed `bounded-native-storage-01` debug cache preserved 671 paths /
235,767,719 unique bytes in an 85,654,337-byte archive. Every payload was decoded
and hashed before retirement. The original source archive, test log, successful
206-test qualification and all 106 distinct external hashes still verify; the
exact target is now empty.

Preparation supervisor 24482/controller 24492, application 43812/43822 and
assessment 48711/48724 all finished successfully. The application child was
43831. The reviewed reservation and explicit workspace-check provenance agree
with all receipts. This is the 57th completed archive, and the first completed
host-cache archive. It qualifies the actual host batch path, not future Cargo
reuse after restoration. No benchmark ran during archival.

See [inventory review](inventory-review.json), [terminal assessment](summary.json),
[child receipt](../host-cache-bounded-storage-01/summary.json),
[selector checks](../host-cache-selector-03/assessment.md) and
[archive regression checks](../cache-archive-qualification-08/assessment.md).
