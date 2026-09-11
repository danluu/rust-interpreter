# Short native bridge blocks: saved-profile screen

Current JIT block boundaries were reconstructed exactly against the saved
compiled-block tables. Restricting the proposal to short chains with compiled
predecessors and destinations, and no unsupported exits, finds 54 candidate
blocks in word64-inline8 and 32 in SHA-1. Only 25 and 6 were executed.

The candidates account for 823,038 executed virtual instructions in word64 and
476 in SHA-1. Conditional edge counts are bounded, not inferred; these counts
are not CPU-time attribution. The profiles precede native block linking, though
the supported-operation and block tables match exactly.

This limited traffic does not justify prioritizing the change over the larger
runtime gap. No short-block implementation or performance experiment was run.
Other short blocks with unsupported exits are outside this analysis.
[Counts and provenance](summary.json).
