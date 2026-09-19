# Proceed to a bounded scalar-padding candidate

The independently closed scope passed1,318,032 alignment-history cases,
51,904 exact byte/canary cases and five invalid-layout rejections. It reused
four closed typed reports and exact saved native self PCs. No compiler or guest
ran. The first attempt failed during import before main; its failure is retained
in bounded-scalar-padding-scope-01, with no commands to replay.

| Capture | All scalar padding samples | One conditional8-byte store | Empty | Other bounded widths |
| --- | ---: | ---: | ---: | ---: |
| ES8 exhaustive | 14 | 14 | 0 | 0 |
| ES8 seeded | 37 | 37 | 0 | 0 |
| Token block | 18 | 18 | 0 | 0 |
| Token exhaustive | 12 | 10 | 1 | 1 |

Every scalar site has a bound allowing either no clear or at most four conditional
stores; none requires the generic fallback in these captures. All sampled ES8
padding is in the zero-or-eight-byte case. This improves coverage over the
closed empty-only proof and removes the full general loop at those sites. These
are sample counts, not timing predictions or proof that a performance gate passes.

Implement only scalar commit padding. Preserve original overflow/capacity,
argument/result guards, private replay, logical budget/profile/peak semantics,
and strict frontend checking. Keep general zero_range and ordinary call clearing
unchanged. Validate emitted bytes/canaries/registers and retained call histories,
then exact guest profiles and a prospectively declared changed-source ES8 screen.
