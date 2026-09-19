The corrected scope is CLOSED. It reused the first successful metadata output
from the preserved failed scope01, then ran only three remaining release metadata
commands (0.94145 s wall, 0.84697 s child CPU). No original guest executed, and no
machine code was published. Closure independently recomputed all four attributions,
checked complete retained evidence/source bindings, and reconciled every original
ordinary-clear sample. All fine labels are unambiguous.

| Capture | Generated self samples | Ordinary clear | Padding setup | Padding chunk loop | Padding byte loop | Other clearing/setup |
|---|---:|---:|---:|---:|---:|---:|
| ES8 exhaustive | 797 | 56 | 6 | 0 | 22 | 28 |
| ES8 seeded | 609 | 38 | 8 | 0 | 19 | 11 |
| Token block | 1933 | 115 | 8 | 0 | 20 | 87 |
| Token exhaustive | 1429 | 88 | 0 | 1 | 8 | 79 |

The ES8 hot ordinary call is caller216/pc115 to265 (seeded222/115 to271): caller
alignment16/extent153, callee alignment16/extent40. The byte loop owns17/19 samples
there. All75/100 ES8 dynamic-prefix sites have payload >= alignment; token has
1263/1285 and1443/1484 such sites. These are coverage counts, not speedup forecasts.

Proceed with a new ordinary-only mechanism: after the unchanged admission guards,
for alignment A<=16 and payload P in[A,256], clear [old_end,old_end+P) with existing
fixed stores, then clear the A-byte range ending at complete_new_end. Actual padding
p satisfies0<=p<A, so the two ranges overlap, cover exactly P+p bytes, and neither
store extends outside the already checked live frame. Keep the existing fixed
empty-padding path first, and keep existing dynamic clearing for ineligible layouts.
This removes the padding loop and its empty branch without reviving the parked
scalar candidate or changing scalar clearing. Verify complete byte canaries and live
registers, retained-alignment histories and whole-VM resource/fault semantics before
real changed-source comparisons. No performance claim or default adoption yet.
