# Reversible cache archival passes fixture qualification

Thirty-seven rejection checks and four coordinator cases pass. The basic
fixture restores five paths from four unique payloads, including a hard-linked
library, executable permissions, an empty file, empty nested directories and
paths with spaces. File and directory access/modification timestamps are
checked directly after restoration. Bounded inspection returns the original
metadata and empty-file contents.

Malformed paths, duplicate/missing/extra ZIP members, altered manifest/payload
bytes, truncation, oversized requests, changed/added source files, open files,
symlinks, special files and extended attributes are rejected. Restore refuses
populated or symlinked destinations.

Coordinator fixtures cover successful retirement, failed archive writing,
failed verification and interrupted retirement. The last case injects a journal
failure after 1,000 of 1,006 fixture paths have been retired. The archive still
verifies and restores all original bytes and hardlink relationships. Both a
blind apply retry and preparation under a new identity are refused. Evidence
outside the target remains unchanged in every case.

The [first qualification](../cache-archive-qualification-01/summary.json) exposed
a test mistake: recovery compared against an earlier fixture snapshot rather
than the exact prepared manifest. Reads can change access timestamps between
those snapshots. That failure, its source snapshot and journal remain preserved.
Qualification02 corrected the test and passed; qualification03 additionally
checks restored access/modification timestamps before further reads.

These are owned fixture operations. **No real compiler cache was modified by
the qualification.** Actual public targets still require independent completed
workflow evidence, a closed-file check, an exact reviewed inventory, sufficient
space for the compressed copy and full archived-payload verification before
retirement. The format does not recreate inodes, ctimes, birth times or ACLs;
special files, external hardlinks, file flags and xattrs are refused. Restoring
bytes does not establish identical future Cargo cache behavior.

[Checks and source hashes](summary.json)
