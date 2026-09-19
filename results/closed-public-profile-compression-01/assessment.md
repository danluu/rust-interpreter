# Closed public profiles preserved with lower disk allocation

All176 JSON files across23 explicitly named, independently closed public profile
runs retain their original normal-read and mmap SHA-256 hashes, modes, ownership,
modification times and exact native creation times. Transparent compression
preserves their paths and ordinary readers. No cache or evidence file was deleted.

Original allocation was6,559,932,416 bytes. The controller recorded1,018,576,896
after compression; independent readback recorded985,337,856 bytes, for a reduction
of5,574,594,560 bytes (5.19 GiB). Allocation snapshots are not permanent guarantees.

The first closure attempt failed45-second shared-lock admission before checking
files. The second failed whole-stat equality. A fresh, separately recorded reader
verified all bytes and metadata and accepted only positive, nonincreasing block
counts:65 files had allocation-only decreases by the final readback. The original
failed reader, receipts, logs, records and summary remain unchanged. This evidence
does not determine the filesystem mechanism behind those allocation changes.

No guest command, Rust build or performance measurement ran. Recompute available
space and the existing build floor before qualification; preserve the shared
build target, installed tools, private data and peer workloads.
