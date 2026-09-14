# Oversized-function coverage diagnostic

All three fresh-owner profiles pass on the current full-parser artifact: adopted
entropy record, adopted replay and broad demand replay. Original per-PC logical
counts, peak guest memory (4,690,279 bytes), entropy consumption and reconstructed
native operation maps agree. This is coverage evidence, not a timing comparison.
The closure verifies 24 frozen inputs and 16 raw artifacts.

`reduce_cold` contains 140,615 bytecode operations. Adopted whole-function emission
leaves all 4,547,956 executed logical operations interpreted. Demand emission
moves 4,371,681 (96.12%) into native regions, leaving 176,275 interpreted. Across
the test, interpreted operations fall from 4,831,199 to 1,008,202 (79.13%). Total
logical work remains 545,134,243. Native scalar work changes, but its original
instruction expansion remains exact.

The demand arena uses 16,777,168 bytes, just 48 bytes below its unchanged 16 MiB
limit. The large function occupies 8,376,668 bytes in 12,127 published regions;
some previously native work elsewhere falls back as the arena fills. Retained
plan payload is 12,114,321 bytes and publication metadata 5,591,518 bytes, each
within its separate 16 MiB bound. These are charged allocations, not total RSS.

The broad demand candidate e5ddb4243a90 / VM b1fd894de0fe remains parked after its
complete failed token primary. The next independent policy uses the existing
65,536-PC CFG-analysis bound: enable program-wide demand preparation only when
the immutable program contains a function above that bound. Compaction of the
surrounding functions matters to arena capacity, so restricting demand to the
large function alone is not supported by this diagnostic. Smaller programs keep
eager preparation. This generic policy needs fresh build, strict/cache, profile
and changed-source performance qualification; no adoption is justified yet.

[Summary](summary.json), [closure](closure.json),
[prospective diagnostic protocol](../../benchmarks/experiments/demand-large-function-profile/PLAN.md).
