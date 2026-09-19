# Recover the remaining VM-build reserve without discarding evidence

Workspace01 passed Python and both Rust profiles but stopped before its standalone
VM build when the shared target's increased allocation raised the required floor.
Do not clean that target or repeat the completed tests. Compress only the exact
ten owned closed public diagnostic runs named in compress_profiles.py. Their
selected JSON files already have hashes in their original closure manifests.
No private run, peer worktree, source, binary, cache or active output is selected.

Reuse the closed176-file compression procedure and exact-birthtime qualification:
original remains until an adjacent copy passes normal/mmap SHA and metadata checks;
verify unchanged identity and no open file twice; atomically replace only on lower
allocation. Preserve mode/ownership/mtime/exact creation time. Record intentional
inode/ctime/compression-flag changes. Never replay an interrupted inventory.

Independent readback follows the now-qualified allocation rule: exact bytes and
all identity fields except blocks must equal the controller's record; only
positive, nonincreasing allocation is permitted and separately recorded. Hold
the shared lock45s,12GiB initial/8GiB children. No guest or timing command runs.
After closure, recompute build admission and resume only the missing VM command.
