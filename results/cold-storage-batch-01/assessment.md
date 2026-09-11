# Preserve six completed caches for the next cold history

All six reviewed inventories completed under the same hash-bound batch plan.
The archives preserve 99,327 paths and 15.06 GiB of unique payloads in 5.07 GiB.
All child payload verifications completed before retirement; the final assessment rechecked 221 distinct external evidence/source hashes.

| Completed workflow | Cache | Paths | Archive GiB |
| --- | --- | ---: | ---: |
| lightweight-wrapper-nushell-cold-01 | check | 7,592 | 0.59 |
| lightweight-wrapper-nushell-cold-01 | baseline | 10,409 | 0.89 |
| lightweight-wrapper-nushell-cold-01 | candidate | 10,409 | 0.89 |
| interface-nushell-repeated-01 | candidate | 23,639 | 0.90 |
| lightweight-wrapper-nushell-repeated-01 | baseline | 23,639 | 0.90 |
| lightweight-wrapper-nushell-repeated-01 | candidate | 23,639 | 0.90 |

The [inventory review](inventory-review.json) records the exact reconstructed
targets, original hashes, permissions/attributes, closed-file checks and
preserved artifact counts. The [completion summary](summary.json) records every
archive hash and the terminal batch receipt. The existing single-target helper
held its benchmark/invocation locks, decoded every payload, rechecked originals
and preserved reports and executed snapshots. No automatic partial retry occurred.

Available space was about 22.67 GiB before cold02 launched. Storage work was
outside benchmark timing; shared APFS activity prevents attributing every free
byte change to this batch. The controller only serializes the qualified helper
and checks its fixed plan hash and untouched inventories. All original cold
orders, source edits, tools and timing gates remain unchanged.
