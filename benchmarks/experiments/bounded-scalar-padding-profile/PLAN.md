# Compare exact original-test execution before an ES8 edit screen

Use the closed full-workspace VM snapshot and adopted df4006 VM. Execute the two
original ES8 tests, token block/exhaustive, and folded-reference test once per VM:
baseline records fresh entropy and candidate replays it. Preserve assertions,
limits and original artifacts/catalogs. This is correctness profiling, not timing.

Require exact per-PC logical counts and all non-timing counters (including peak
memory, scalar/native/ordinary instruction accounting and zero JIT declines).
Validate complete native maps against each process/code/profile. Match the exact
baseline scalar-padding48-byte sequence and the ten possible bounded sequences;
qualify shape/mutated-word/alignment controls before guests. Paired native spans
must retain identities, and only Call spans containing the baseline helper may
shrink by exactly its replacement's size (including proven-empty removal). All
other span sizes remain equal. General helpers may remain for larger alignments.
No assertion of byte equality across relocated or ASLR-dependent branch targets.

Ten guest commands, one active child, shared lock45s,12GiB analysis admission,
8GiB before each guest and closure. Freeze controllers, sources, VM snapshots,
artifacts, catalogs, entropy library and qualified map observer through terminal
and independent closure. Preserve failed/passed prefixes; never replay a guest
solely to repair its report. Default installation remains unchanged.
