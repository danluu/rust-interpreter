# Token screen storage admission, before first timing

The former 9.5 GiB admission / 8 GiB reserve was a blanket workflow rule.
The exact completed twelve-test register-allocation screen supplies a closer
storage estimate for this same source, test set, native profile and four-cache
layout. Its preserved inventory and evidence sizes are recorded in
results/constant-fold-storage-sizing-01/summary.json.

| Retained or regenerable data at completion | Logical bytes |
| --- | ---: |
| Native Cargo cache | 722,189,104 |
| Check Cargo cache | 169,198,782 |
| Baseline custom Cargo cache | 238,487,657 |
| Candidate custom Cargo cache | 238,487,754 |
| Selected artifacts and all other raw screen evidence | 472,530,878 |
| Total | 1,840,894,175 |

This is 1.7145 GiB, including preserved files and regenerable files. It is a
terminal size, not a measured peak. For the first constant-fold **token** screen,
admit at 6.5 GiB and retain a 4 GiB floor before each child. The resulting 2.5 GiB
growth budget exceeds the preceding complete run by 0.7855 GiB. The installed
compiler/VM and standard metadata need no rebuild or download. Record actual
free space before each child, preserve all evidence and restore the edited
source on an ordinary stop. If the floor is crossed, the screen is incomplete;
do not delete other work, silently lower the floor again or call it a pass.

This changes resource admission before any candidate timing. Both compiler
modes still get fresh, separate caches and the same complete commands. The
five-edit pairing, all twelve original tests, wrong-edit control, exact artifact
verification, 10% wall gate and no-CPU-regression gate are unchanged. No timing
result motivated this sizing revision. Other project screens and host build
rules keep their existing thresholds. Optional external placement checks both
the cache and evidence filesystems against this same reserve.
