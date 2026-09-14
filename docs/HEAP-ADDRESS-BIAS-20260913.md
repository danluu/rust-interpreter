# Heap address bias: full token gate failed; runtime parked

The initial 40-command changed-source token screen passed narrowly: paired wall ratio
0.971177 (2.88% improvement) against a 2.747% A/A envelope; paired CPU ratio
0.994053. Candidate/native wall ratio is 1.62412. This admits the full comparison;
it does not justify runtime adoption. All original assertions, intentional wrong
edits, source restoration and cached artifact identities pass.

The candidate hoists heap host-base bias and virtual-end construction to external
native entries, keeping raw guest addresses through complete checked ranges.
It preserves the original unsigned arena selection, null/heap-zero rejection,
read-only limits, fault order, empty accesses and cached registers. It starts
from main ab6adbe8 and includes neither failed tree bridge nor successor flush.
The runtime patch remains on experiment/heap-address-bias-20260913.

Candidate tool 5929f04f / VM d6a081f4 is compared with an unchanged ab6adbe8
control, tool 4a1381c4 / VM 8f08254c. Both retain the exact cf4b3499 exporter and
45bca4f2 wrapper. Qualification passes 553 workspace tests in each profile,
119 strict/cache commands, and six matched executions across the three original
profiles. Actual emitted address checks pass independent wide-integer boundary
oracles. All per-PC logical counts, memory and entropy match. Control code
matches the adopted reference exactly on these three profiles.

Code size alone would have given the wrong decision: block code grows 12,316
bytes, exhaustive code shrinks 24,348, and folded code grows 6,748. Entry setup
adds bytes while repeated checks lose bytes. The profile audit accounts for
context setup inside transition spans as well as entry spans. Neither code
size nor saved sampled PCs is treated as a latency estimate.

All failed setup/diagnostic controllers remain recorded. A shared Cargo target
across two source copies reused the unchanged production VM after candidate
tests passed. Its candidate qualification was revoked before any guest benchmark.
A fresh isolated target produced the distinct qualified VM; exact emission
checks verify the intended mechanism. The two completed original block profile
executions were reused after correcting offline accounting, without rerunning
the guest prefix. The closure verifies 2,291 evidence files and 597 Git source
bindings; the rejected tool ran zero benchmark commands.

All 13 selected/prepared real controls and 23 full-protocol controls pass. The
fresh 154-command full token history then fails the performance gate: paired
wall ratio 0.989751 (1.02% improvement) versus 3.8043% A/A; CPU ratio 1.001508
(0.15% regression). CPU plus its 1.1659% envelope remains within 1.05, but the
separate no-regression ceiling fails. Candidate/native wall ratio is 1.624861.
All original 12 assertions, three intentional wrong states, three five-edit
histories, final restoration and artifact identity checks pass. The final
source and frozen-input audit passes.

Park the runtime and preserve the narrow screen result alongside the failed
full result. Folded, pgrust, private rg-aot, Nushell and complete-parser guards
remain unstarted. No quiet retry or repeated primary/full history follows.
Inspect saved native code for constant-materialization costs before choosing
a different candidate. The adopted runtime on main remains unchanged.

Evidence: [full token](../results/heap-address-edit-token-01/summary.json),
[closed campaign](../results/heap-address-full-01/summary.json),
[final audit](../results/heap-address-full-01/final-audit.json).

Closed primary compiler intermediates were retired only after the closure and
exact ownership/open-file checks. Transparent filesystem compression preserved
the bytes, paths and modification times of 24 closed diagnostic JSON files,
recovering about 1 GiB. Timed artifacts and executable files were excluded.

Evidence: [primary](../results/heap-address-screen-token-01/summary.json),
[closure](../results/heap-address-screen-token-01/closure.json),
[matched profiles](../results/heap-address-profile-03/summary.json),
[qualified build](../results/heap-address-build-03/summary.json),
[compression](../results/closed-diagnostic-json-compression-01/summary.json).
