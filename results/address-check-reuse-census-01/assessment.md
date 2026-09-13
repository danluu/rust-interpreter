# No repeated same-register address checks in the measured regions

All ten offline commands pass: three typed profile/bytecode comparisons and
seven CLI rejection controls. No guest code executes and no emitter behavior
changes. No function hits an analysis limit.

| Test | Native Load/Store observations | Already frame-local | Remaining validations | Fully reusable |
| --- | ---: | ---: | ---: | ---: |
| Token block boundaries | 3,141,495,906 | 2,945,037,751 | 196,458,155 | 0 |
| Token exhaustive semantics | 2,344,454,916 | 2,303,205,693 | 41,249,223 | 0 |
| Folded short strings/windows | 734,932,388 | 724,723,257 | 10,209,131 | 0 |

These are logical operations weighted by observed native-region entries, not
hardware memory traffic. Existing forwarding may eliminate a local load.
The census models the existing Local/Imm facts, exact pointer-register
identity, checked byte extent and read/write permission. Definitions,
region boundaries, opaque effects and the bounded cache invalidate proofs.
It does not establish that more elaborate alias analysis has no opportunity.
It provides no reason to implement the proposed exact-register check cache.
Drop that implementation path; do not repeat this census to seek a positive
result or weaken its validity conditions.

The [store-category census](../known-local-memory-census-01/summary.json)
instead finds 1,001,567,587 / 908,006,981 / 354,217,968 stores of at most eight
bytes. Subtracting every nonlocal access from all common-size stores gives
conservative lower bounds of 805,489,036 / 878,277,040 / 358,069,180 known-local
common-size stores. This supplementary categorization uses already verified
profile operation text only for counting, not for semantic safety proofs.

Next investigate simpler memory instruction generation: drop overwritten
temporary load clears, omit the unused high-word source read for narrow
stores, and fold proven local offsets into existing hardware memory operands.
Preserve full VM-register initialization, bounds/permission validation and
fallback paths. Qualify a separate candidate before measuring complete edited
commands; neither these counts nor fewer emitted words establish a speedup.

The initial census build failed before tests due to a missing size conversion;
the corrected build passes 426 tests per debug/release profile. Both receipts
remain in results. The qualified executable SHA256 and all source/profile
hashes are retained in the machine-readable summaries and raw records.
