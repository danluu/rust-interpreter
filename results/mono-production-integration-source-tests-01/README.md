# Per-item compiler support: source checks

At e7d2dd48, 111 focused Python tests passed in 0.935 s, and the complete Rust
workspace passed 490 tests with one existing artifact-census test ignored.
The Rust tests used the pinned public nightly compiler, release profile,
locked/offline dependencies and two jobs in a fresh owned target directory.
Both runs acquired the canonical workload lock.

The checks cover the combined opt-in per-item routing, actual-argv recording,
source-containing std preparation, strict diagnostic mapping and screen
validation alongside existing launcher/workspace behavior. This is not a
qualification of the patched compiler: no per-item stage2 compiler, real v2
std preparation, 36-command custom integration or per-item timing ran here.
The explicit new mode still requires separately qualified compiler/tools/std
identities; the earlier compiler cannot be relabeled to satisfy it.

The archive contains 336 exact files, including both completed process and
supervisor receipts, unabridged test logs, runners, and the tested Python/Rust
source snapshots. All member lengths/hashes and the compressed archive hash
were checked. No benchmark or holdout commands were executed.
