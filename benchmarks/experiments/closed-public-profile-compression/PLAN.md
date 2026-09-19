# Preserve closed public profiles while recovering build headroom

Compress only the exact 23 owned, independently closed public profile runs named
in compress_profiles.py. Each selected JSON file must be at least 1 MiB and its
plaintext SHA must already occur in that run's hash-bound closure manifest.
Failures remain failures. No private data, binaries, source trees, compiler
caches, installed tools, or shared build target are selected.

Reuse the qualified ditto transparent-compression and exact native birthtime
helpers. Require single-link regular nonexecutable files, no symlinks, no ACLs or
unexpected xattrs, unchanged identity, and no open descriptor before copying and
replacement. Preserve plaintext through normal and mmap reads, mode, ownership,
mtime and exact creation time. Replace atomically only when allocation decreases.
Inode, ctime and compression flags intentionally change; paths and bytes do not.
Keep each original until the adjacent temporary copy is fully verified. Save
progress before replacement; never replay an interrupted inventory automatically.

Use the shared benchmark lock (45 seconds), 12 GiB initial and 8 GiB per-file
admission. Bind helper qualification, controller sources, historical closures,
terminal receipts and manifests, and ditto identity. Independently close by
checking every final plaintext hash and metadata tuple and the terminal receipt.
This is storage maintenance, with no guest command or performance measurement.
Recompute the Rust build floor after closure; do not infer admission from savings.
