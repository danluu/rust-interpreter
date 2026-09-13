# Select the composition for correctness qualification

All three offline comparisons reproduce the saved baseline native bytes and
operation maps exactly. The composed treatment preserves local values after
already guarded disjoint writes, retains exact constants/full-width local-pointer
facts after forwarded loads, and folds scalar-copy address operands through the
existing guarded and local memory paths. No alternative guest code ran.

| Profile | Baseline bytes | Composed staged bytes | Additional weighted forwards | Lost forwards |
| --- | ---: | ---: | ---: | ---: |
| Token block boundaries | 12,166,780 | 11,683,208 | 63,278,658 | 0 |
| Token exhaustive partitions | 14,770,152 | 14,159,104 | 125,602 | 0 |
| Folded matching | 2,052,192 | 1,972,096 | 11 | 0 |

No function declined under the cumulative 16 MiB staging bound. The primary's
frequency-weighted operation spans shrink by 4,778,210,432 static words, while
flush spans grow by 23,277,488. Successor-fallback spans shrink by 80,962,836;
those paths do not execute uniformly and must not be counted as retired work.
These measurements describe emitted structure and saved region frequencies,
not elapsed time or an expected percentage speedup.

The narrower retention-only and retention-plus-static-facts censuses remain
separate records. The old scalar-copy candidate's failed full performance verdict
also remains unchanged. This composition uses guarded addresses and preserved
static facts that were absent from that earlier treatment.

Select this combined mechanism for runtime qualification on branch
`experiment/guarded-local-facts-20260913`. It has not passed runtime qualification
or an end-to-end timing screen. Debug/release tests, strict Cargo/cache controls,
original real-test profile/entropy replays, and a fresh token-first changed-source
screen are required before any performance decision. Every project guard remains
required for adoption. Normal main runtime behavior is unchanged by this report.

[Summary and evidence hashes](summary.json),
[retention-only census](../guarded-local-facts-census-01/assessment.md),
[static-fact composition](../guarded-local-facts-static-census-01/summary.json).
