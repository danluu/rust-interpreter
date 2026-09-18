# Exact origins retain most of the load coverage

Twenty controls pass across eight commands. Both adopted native captures and all
broader first-census counts reconstruct exactly. The narrower model retains
**86 block / 40 exhaustive** payload-load samples with a single same-width origin
and a free temporary slot, versus 109/51 available-byte samples initially.

| Remaining sampled loads with assigned origins | Block | Exhaustive |
| --- | ---: | ---: |
| Load, 1 byte | 2 | 1 |
| Load, 4 bytes | 10 | 0 |
| Load, 8 bytes | 26 | 24 |
| Copy, 1 byte | 3 | 0 |
| Copy, 4 bytes | 17 | 1 |
| Copy, 8 bytes | 19 | 7 |
| Copy, 16 bytes | 9 | 7 |

All 7,717/9,434 reused origins fit the modeled fifteen-slot pool, covering
9,719/12,597 static reuse sites. These are static generated bodies, including
unexecuted paths. Many origins have only one later use; capture and extraction
cost may consume their benefit. No instructions were emitted for the proposed
slots, and this is neither an ABI-preservation proof nor a timing result.

Proceed toward a bounded model that retains complete values while keeping every
original frame write. That narrower mechanism can preserve captures across
non-writing operations without the deferred-publication fault obligations of a
virtual frame. Unknown writes and native-region entries remain barriers. Require
concrete-value differential controls, audited temporary-register preservation,
and capture-cost filtering before an emitter or changed-source screen.

Source `9dd2ecc3`; exact raw origins, intervals, samples and source bindings are
linked from [summary.json](summary.json) and [closure.json](closure.json). No guest
execution, code publication, runtime adoption or larger benchmark history.
