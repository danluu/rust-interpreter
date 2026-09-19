# Independent file-table reader qualification

All 22 focused controls passed once, followed by an independent audit of the
exact 15 frozen inputs, raw outcomes, process associations and closed terminal.
The verifier reconstructs the full file table without importing the producer
helper. Tests compare both implementations and cover typed metadata, complete
selection, forged integrity, changed bytes, symlinks and post-read route changes.

The manifest retains every tested input and maps each exact evidence copy to its
original path, hash and identity. Original source documentation remains frozen
with its pre-execution wording. System binaries are evidence bytes only.

This qualifies the reader against small fixtures. The hash-driver workload,
runtime installation and application build timings are separate qualifications.
No sub-0.5-second result is established.
