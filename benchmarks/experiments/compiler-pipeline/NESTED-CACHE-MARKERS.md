# Preserve the additional target-directory markers

The first completed custom-cache preparation correctly derived its namespace
and executed-artifact paths, then refused xattrs below the cache root. Read-only
inspection found the same two Cargo markers on `target/aarch64-apple-darwin`
as on `target` itself. No archive or reservation was created and no file changed.
The [refusal](../../../results/interface-nushell-baseline-cache-archive-01-prepare/summary.json)
preserves the exact path and attribute inspection.

Finish the already prepared native archival before changing its frozen helper
sources. Then extend metadata preservation to this one observed architecture
directory. Keep the same attribute-name and value-size bounds, require the
directory to appear in the validated inventory, and reject attributes on files
or any other nested path. Store the optional directory/value map separately
from the existing root field so old archives remain restorable.

Qualification must restore exact root and architecture-directory values along
with bytes, modes, times and hardlinks, including partial-retirement recovery.
Reject unknown directory names, absent inventory directories, unsupported
attributes and malformed values. Preserve the existing refusal for markers on
an unrelated nested directory. Then prepare a new custom-cache inventory,
review it separately, hold its invocation lock, and apply the same complete
write/decode/hash/recheck/retire sequence.

These changes provide storage for the predeclared cold histories. They do not
alter compiler tools, commands, source edits, sample counts, timing gates or
the eight-GiB command guard. All reports and executed snapshots stay in place.
