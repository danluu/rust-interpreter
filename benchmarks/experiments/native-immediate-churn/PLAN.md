# Explain body invalidation before designing a native cache

The closed native-reuse identity census finds thousands of changed function
bodies on some real edits, with unchanged global mode and mostly unchanged
layouts. Investigate which exact opcode fields changed before proposing a
persistent cache or a relocation scheme. The ordinary allocator already weights
backedges; do not start a redundant loop-weighting candidate from that premise.

Reuse all 14 consecutive artifact transitions from that census's two eight-state
histories. A test-only typed observer validates both programs, compares complete
function encodings and partitions changes into exact immediate-value-only changes
versus all other changes, requiring identical names, layouts, opcode positions,
destinations and lengths for the first class. Preserve full u128 literal values.
Reconcile changed function IDs with the separately closed digest census.

Report literal deltas and whether the numeric values happen to fit the two data
segments and index equal 16-byte windows. These are ambiguous observations:
ordinary integers can satisfy them, and data may contain zeros or repeated bytes.
No inferred pointer provenance, cache-key normalization, executable patching or
production change is authorized by this diagnostic. A correct future relocation
scheme would need explicit provenance and every code-generation dependency.

Two controls cover full-width values, changed names/layouts/opcodes/destinations,
and deliberately ambiguous integer/data matches. Run one release test command
(controls plus saved-pair observer), no guest. Use the existing ROOT target,
two Cargo workers, the shared lock, max(14 GiB, 8 GiB + twice allocated target)
build admission and an 8 GiB child floor. Bind and close all inputs and outputs.
