CLOSED: zero compiler/guest children, complete typed-site and exact-PC reuse,
all original ordinary-clear samples reconciled, zero ambiguous samples. Every
large-frame helper matches the exact20-word batch-plus-tail sequence. Controls
reject20 word mutations and unaligned/truncated patterns and verify five branch
targets. Current production source equals adopted24cd8e99.

| Capture | Generated samples | Large-frame samples | 64-byte stores | Byte-loop control | 16-byte-loop control | Other |
|---|---:|---:|---:|---:|---:|---:|
| ES8 exhaustive | 797 | 23 | 17 | 4 | 2 | 0 |
| ES8 seeded | 609 | 0 | 0 | 0 | 0 | 0 |
| Token block | 1933 | 79 | 37 | 28 | 11 | 3 |
| Token exhaustive | 1429 | 73 | 45 | 21 | 7 | 0 |

All sampled large frames have alignment<=16. Static large sites are58/65/1216/1439;
only one site in each token capture has larger alignment, neither sampled. The
required64-byte stores dominate much of this bucket and cannot be counted as
removable. Remaining loop control is about2% of generated token samples and less
on ES8. This is a limited opportunity, not a forecast of a whole-command win.

Proceed with a separately isolated large-frame-only fixed-trip-count candidate,
using token as the prospective primary because both token assertions exercise the
remaining control bucket. For payloadP>256/alignmentA<=16, clear exactlyP bytes
using floor(P/64) iterations of the existing four pair stores and fixed residual
stores; then clear the end-anchoredA-byte tail only if the retained-alignment
proof cannot establish zero padding. This targets the dynamic residual loops
left unchanged by the earlier wider-store experiment. Small-frame/scalar helpers
stay adopted; do not revive or bundle either parked candidate.

Require byte/register canaries including every residual and empty/dynamic padding,
retained histories and full VM limits, then full workspace checks and original
assertions before a prospective real-edit token screen. Reuse closed immutable
adopted profile/code/entropy controls where possible instead of rerunning identical
baseline guests. Any screen failure parks the new candidate. Prior thresholds,
strict checking, exact memory initialization and held-out gates remain binding.
