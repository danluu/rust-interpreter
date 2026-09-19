# Native and Miri tests passed; compiler integration outstanding

The actual proc_macro crate passed all 13 tests: ten Arena tests and three
Interner tests. The ten Arena tests also passed independently under Miri's
Stacked Borrows and Tree Borrows models, with empty diagnostic streams.

The focused, unchanged original Arena failed both Miri models at its shared
slice read in last_chunk.len(). Version04 removes that read by recording the
chunk capacity separately. Earlier source proposals, native passes, setup
failure and aliasing failure are all preserved.

Evidence is in ../../results/proc-macro-arena-crate-05,
../../results/proc-macro-arena-miri-05, and
../../results/proc-macro-arena-stock-miri-01. The original source-only README and
source-review.json remain unchanged snapshots. No new compiler distribution,
application benchmark or performance result has been produced for this patch.
Bridge integration and real compiler/client qualification remain outstanding.
