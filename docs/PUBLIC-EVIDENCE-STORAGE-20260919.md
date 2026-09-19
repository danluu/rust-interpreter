# Retain completed evidence with less allocated storage

Transparent macOS compression reduced373 completed public bytecode copies from
10,960,859,136 to3,113,185,280 allocated bytes, about7.31GiB less. The independently
[closed operation](../results/closed-public-artifact-compression-02/summary.json)
verified every original plaintext SHA256 and preserved its path, size, mode,
owner, modification time and creation time. Inodes, change times and compression
flags intentionally changed. Ordinary reads and memory mapping still work.
Actual free space was about24.7GiB afterward; allocated savings are not a promise
about volume headroom under concurrent work.

Only exact manifest-listed artifact copies from completed public experiments
were selected. Compiler caches, sources, installed tools, native executables,
private workloads and other sessions were excluded. Every replacement followed
full hash/metadata validation and an open-file check under the benchmark lock.
The two read-only inventories and all original timing results remain intact.
The inventories record historical inode identities; do not rerun them or the
mutating operation as if those original identities still existed.

The first operation stopped after132 replacements: ditto changed creation time
on its next temporary copy. That original was never replaced. A disposable
recovery probe then showed that opening a compressed copy with write access
decompresses it and changes modification time. Both failures are retained. The
corrected probe uses a read-only descriptor for metadata-only fsetattrlist and
checks exact native creation seconds/nanoseconds with distinct modification time.
Its [independent closure](../results/closed-public-artifact-compression-recovery-02/closure.json)
preceded the241-file continuation, which consumed the existing pending copy and
left the132 completed originals alone. No compiler or guest workload was rerun.
