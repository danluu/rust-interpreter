# Preserve Cargo's architecture-directory metadata

All 44 rejection checks and four archive coordinator scenarios pass. The
optional directory attribute map accepts only the observed
`aarch64-apple-darwin` directory, requires it in the inventory, and applies the
same two-name/4 KiB value bounds as the root. Other nested locations and file
attributes remain refused.

The fixture deliberately uses different file-provider values at the root and
architecture directory. Both restore correctly with exact payloads, internal
hardlinks, permission bits and access/modification times, including recovery
after 1,000 fixture paths have been retired. Invalid directory names, absent
directories, unknown attributes and malformed values are rejected. Both older
archive layouts (without attributes, and with root attributes only) restore.

Supervisor 11795 and worker 11798 finished with status 0. The [summary](summary.json)
records exact source hashes and preserved fixture values. No real compiler
cache was modified by this qualification. The prior real custom-cache refusal
remains preserved; a new preparation is required before archiving that cache.
