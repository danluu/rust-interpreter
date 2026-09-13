# HIR input-coverage diagnostic qualification

The exact-gate public compiler driver built and passed all 54 recorded commands
on the first attempt. Eight successful native states covered original source,
a body edit, an earlier Unicode source shift, restoration and restorations after
four uncalled-error controls. Type, move/borrow, const-evaluation and constant-panic
failures matched the ordinary compiler's complete raw stdout/stderr exactly.
Version and dep-info-only reports were correctly unusable.

The original synthetic fixture had 15 resolver owners, no unvisited owners, and
four eligible free functions out of nine. Their encoded resolved inputs totaled
1,843 bytes; observed candidate-format keys totaled 2,255 bytes. These are fixture
coverage facts, not project coverage or evidence of HIR cache hits or speedup.
The compiler cache patch itself remains uncompiled and unqualified.

`summary.json` identifies the actual binary and source producer. The verified
archive retains all command/process receipts, raw output, reports, source snapshots,
helper snapshots and compiler/tool identity documents. Binaries and incremental
caches remain in the owned local run and are not duplicated in this archive.
All 328 frozen public compiler input files and the loader/source guards were
revalidated unchanged; the fixture was restored. No project or holdout was run.
