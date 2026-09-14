# Scalar private transfer opportunities

Both census revisions pass their path controls and reconstruct all 137 saved
private-ABI scalar bodies without guest execution or executable publication.
The current census counts successful calls only; failed attempts are excluded.

| Original case | Fixed-step calls | Zero-result calls | Narrow captures |
| --- | ---: | ---: | ---: |
| Token block | 6,756,060 | 6,319,612 | 38,228,142 |
| Exhaustive token | 4,385,605 | 13,938,012 | 78,573,960 |
| Folded prefilter | 1,585,153 | 1,585,101 | 75,010 |

No empty arguments occur in these profiles. Fixed success lengths agree exactly
with every original successful PC count. Structural paths with unequal Return
lengths decline a constant even when a path might be infeasible at runtime.

Try one private transfer candidate: narrow arguments capture only their readable
low lane; zero-byte results omit private result/destination transfers; a proved
fixed success length substitutes for the dynamic private counter. Retain all
original resource/fault guards and original budget admission. Dynamic counts
remain for varying paths. These overlapping counts are neither measured hardware
traffic nor an end-to-end performance estimate. The prior private ABI primary
remains failed and is not repeated unchanged.
