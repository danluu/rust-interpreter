# Resumable cursor field census

| Case | Cursor samples | Budget loads/stores | Budget share of thread samples | Ambiguous |
| --- | ---: | ---: | ---: | ---: |
| folded | 231 | 154 | 7.54% | 0 |
| token | 1073 | 761 | 10.06% | 0 |

All 1,304 cursor samples reconcile with the existing six exact-code profiles. Budget access accounts for 761 token samples: 484 in ordinary resumable regions, 171 in Calls and 106 in Returns. Other cursor state remains separately reported. Field layouts match the pinned compiled Rust assertions. No new guest execution or runtime change was made.

The first attempt could not obtain the benchmark lock and performed no analysis. Its failure and source snapshot remain preserved. A distinct attempt completed after the lock was released; no other process was controlled.

This is an address/field attribution, not a speedup prediction. It supports investigating a native register for the remaining instruction budget, with exact charges and publication on every VM exit. Calls/Returns currently use x22 as a temporary; freeing it requires an explicit clobber and fault-order audit.
