# Bounded scalar padding: inconclusive; park the candidate

All40 end-to-end commands and two fresh strict probes completed and were
independently closed. Native/custom outcomes match for original, deliberately
wrong, all five valid edits and compiled restoration. All custom artifacts and
catalogs match. Unreachable E0308/E0499 errors were rejected before export or
execution. Attempt01 had no commands or edits: its lock-admission failure is
closed separately, and attempt02 reused the unchanged qualified adapter.

The prospectively declared performance gate did not pass:

- Median paired candidate/baseline wall ratio:1.061625159 (+6.16%).
- Maximum absolute identical-control wall deviation:0.374148503 (37.41%).
- Median paired CPU ratio:1.032446461 (+3.24%); CPU control envelope:24.88%.
- Candidate/native paired wall ratio:1.570663710.

The wall requirement was ratio<=0.99 and ratio+the complete A/A envelope<1;
the observed sum is1.435773662. The envelope exceeds8%, so the recorded verdict
is unmeasurable. Do not claim an established6.16% regression, a speedup, or a
zero mechanism effect. Keep all five pairs and all setup/wrong/restored costs.
Park candidate d4aba7b8; no unchanged retry or held-out adoption campaign.
Default df4006 and production main remain unchanged.

A descriptive stage audit of the retained rows shows the large fluctuations
span both Cargo and guest execution. At edit2 the duplicate Cargo stage was
1.537s/1.269 CPU versus baseline0.860s/0.776 CPU; guest wall was1.821s versus1.589s.
At edit4 the candidate Cargo stage was1.463s/1.245 CPU versus baseline1.016s/
0.835 CPU; guest wall was1.763s versus1.327s. These observations do not identify
a cause, but they do not isolate the variation to the changed clearing helper.
No row was discarded or adjusted, and no other process was controlled.

The qualification remains useful:21 focused tests/profile,613 workspace tests/
profile,446 Python passes, five exact original-test profile pairs, and emitted
scalar code reductions2968/2936/13788/17148/944 bytes. Static and correctness
wins are insufficient evidence for runtime adoption.

Next restore the exact adopted runtime on a new branch and scope the ordinary
padding helper separately from payload stores in the existing captures. Its
sampled coverage must be established before a larger candidate. Consider a
prospective identical-control admission check for future candidates if continued
host variation makes the current gates unable to resolve useful gains; never
use it to select favorable rows or revive this completed screen.
