# Persistent payload verification

The eight-state fre tokenization history passes with exact retained bytecode
and unchanged assertions. This includes the expected wrong-edit failure and
a restored-source rebuild. Each edited build actually reads prior-session
payloads: 5,178–5,202 functions are reconstructed from them; 172 unsupported
recipes continue through full lowering. All original lowering also executes.

The 61,236,722-byte original cache file is finalized by rustc. Small controls
pass 50 debug/release exporter tests, 231 complex-fixture commands, 229 semantic
edit commands and 98 cache-fault/publication commands. Corrupt, wrong-namespace
and missing payload files trigger full regeneration. Trap/callback policies
change both payload namespace and compiler node identity. A bytecode publication
failure after staging adds no finalized session; the next build recovers.

The first semantic harness attempt stopped because it incorrectly required
rustc to retain every older finalized generation after a source error. Pinned
`rustc_incremental/src/persist/load.rs` runs generation collection during load.
The corrected control requires the newest successful generation to survive,
with no new or changed finalized payload. The failed attempt remains in
`.work/export-dependency-fixture-03`; it is not counted as a passing suite.

Storage overhead needs improvement before a performance screen. Median edited
intervals are 144.74 ms load (including namespace and integrity work), 139.62 ms
file encoding, 7.78 ms file write and 36.19 ms prior-template decoding. These
already consume much of the earlier ~444 ms cost-weighted reuse opportunity.
The replay diagnostic also includes expensive whole-graph comparisons. None
of these intervals establishes an end-to-end speedup. Next separate those
costs and qualify a mode that actually skips original lowering.

Raw commands, censuses, executed snapshots and finalized-file hashes are in
`.work/export-reuse-token-05`. Immutable matching bytecode snapshots share
retained reference inodes. Exact source/tool identifiers are in `summary.json`.
