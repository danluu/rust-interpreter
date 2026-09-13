# Existing native CGU correspondence

The retained edited and restored Nu Protocol host sessions each contain 256 object files. Between them, 42 edited names disappear, 42 restored names appear, 4 shared names contain rebuilt objects, and 210 shared names retain the same hardlinked inode.

The 42 edited-only objects total 5,983,456 bytes; the 4 shared-name rebuilt edited objects total 7,303,024 bytes. Their sum, 13,286,480 bytes, exactly matches the existing edited self-profile’s 46 generated object files. This is evidence of partition identity churn beyond the 4 rebuilt units that retained their identities. It does not establish that all 42 objects could safely be reused or predict a measured speedup.

The archived receipt contains every retained session file's name, size, inode, device, mtime and SHA256, plus the original edited wrapper 54385/compiler 54386 and restored wrapper 57653/compiler 57654 invocation records and edited query summary. The edited command was instrumented and the restoration was not; their durations are not a valid performance comparison. Exact changed-object binaries remain privately retained under `.work/stable-cgu-source-evidence-01/objects` and are not required to inspect these counts.

No new compilation, test, or benchmark was run to produce this evidence. Source caches were only read and were left unchanged.
