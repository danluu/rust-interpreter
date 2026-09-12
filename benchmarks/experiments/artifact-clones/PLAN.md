# Preserve repeated benchmark snapshots with APFS copy-on-write clones

Scope: the 336 executed public fre snapshots in the two completed, parked
budget-register and guarded-Call primary comparisons. Keep all report paths,
snapshot paths, exact bytes, modes, ownership and modification times. The
reports describe 5.92 GB of snapshots with substantial identical payloads.
Do not infer physical savings until observing free space after cloning.

Use the macOS `clonefile` syscall, with no ordinary-copy or hardlink fallback.
Apple documents shared data blocks and independent subsequent writes in its
[clonefile manual](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/man/man2/clonefile.2).
File identities, change times and birth times may change. This is preservation
of immutable evidence, not a guest runtime optimization or timing result.

Preparation recomputes all eight original workflow verifications, checks the
exact completed primary reports and external hashes, and inventories every
selected file. Reject private/unknown runs, symlinks, hardlinks, special flags,
extended attributes, ACLs and live files. Bound selection to 1,000 files and
16 GiB. Review and commit the exact inventory before applying it.

For each duplicate, clone its verified canonical peer into a new adjacent
temporary file, restore the destination's metadata, verify bytes and metadata,
and only then atomically replace the still-unchanged original. Journal every
replacement. A failure stops; do not automatically retry an incomplete run.
Canonical peers remain unchanged. Verify every snapshot and all external
evidence again afterwards. Tests must establish independent writes in both
directions, replacement metadata, and rejection without changing the original.

Every action holds the existing benchmark lock, outside timed workflows.
No source/test changes, process control, private artifacts or archived cache
payloads are in scope. The existing benchmark loaders and verifiers keep their
original paths and behavior.
