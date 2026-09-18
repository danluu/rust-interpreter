# Own-thread append/patch transaction qualifies

Corrected source e1466567 passes all 355 bytecode controls in each of debug and
release (13 ignored observers). New controls execute 64 repeated two-entry
updates per profile through the ABI wrapper, plus backward and branch-only
updates. Eleven malformed/stale/unordered batches and two additional target/
capacity refusals preserve the complete old code and executable results. The
initial helper compilation failure remains closed under run 01.

Both adopted captures still reconstruct and reassemble exactly: 20,033/23,406
regions and 11,313,812/13,757,056 bytes. Four commands take 64.516691 seconds.
The closure verifies 309 source/input bindings and ten output artifacts.

All validation precedes writes: aligned committed sites, ordered unique patches,
expected original B words, replacement branch encoding, signed targets within
transaction extent and arena capacity. The same owning thread appends/patches
outside native execution, restores write protection and flushes changed code.
No metadata or allocation enters the write window; ordinary append uses an empty
patch set. The primitive verifies arena extent, not same-function entry identity;
the upcoming region publisher must establish that stronger condition.

No demand policy or original guest benchmark is enabled. Next bind stable entry
tables, pending edges and assertions in a bounded publication transaction before
connecting the VM loop. Performance remains unmeasured.
