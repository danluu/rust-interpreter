# Transparent compression of exact completed public artifact copies

Use only the independently closed public inventories01 and02, and only regular
single-link non-executable `.rbc` files directly in each completed raw run's
`artifacts` directory. No source, cache, tool, native executable, private workload,
peer worktree or current benchmark input is selected. The historical runtime
screen may have failed its speed gate; its completed evidence is still retained.

Before any mutation, bind both inventory closures and manifests, verify every
selected full plaintext hash and original stat identity, reject flags, ACLs and
extended attributes, and record the entire exact path manifest. Hold the shared
benchmark lock throughout with12GiB admission and8GiB child floor. Check each
source is unopened immediately before copying and immediately before replacement.
Use the already tested native ditto compression with no cloning. Preserve bytes,
paths, size, mode, uid/gid, birth time and exact mtime; inode/ctime and compression
flag intentionally change. Validate ordinary and mmap reads plus complete hash
before atomic replacement. A non-saving copy leaves its original intact.

Each operation records intent before replacement and completion after it. Copy
or validation failure stops without replacing that original. Any leftover copy
or partial operation remains for exact recovery; never restart the mutating run.
Afterward independently verify all plaintext hashes and metadata, both original
inventory proof chains, operation receipts and actual allocated-byte accounting.
Disk admission uses current free space, never estimated or logical savings.
This is evidence storage work, not a performance or guest correctness claim.
