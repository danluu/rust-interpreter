# Repeated end-to-end comparison of compiler routing

Both one-cycle qualifications pass. Pgrust's edited command was slightly faster
with c341; Nushell's cold and edited commands were slower. Keep both observations
separate from the repeated experiment. The original cold improvement threshold
(at least 5%) and warm regression guard (no unresolved median paired regression
over 5%) in LIGHTWEIGHT-WRAPPER.md remain unchanged.

Tools stay fixed: baseline 78e60cdd, candidate c341296c, same VM hash and ordinary
JIT in both, with resumable/persistent calls off. Use the pinned generic API
cases, all original tests and wrong edits, matched leaf inlining, native root
O0/incremental/eighteen jobs/default test concurrency, custom four jobs and
independent checks. Nushell uses the same prebuilt std-MIR. Do not retune jobs,
MIR flags, thresholds or the native profile after seeing these observations.

First qualify `--initial-mode-order` with three pgrust cycles starting in
candidate,baseline,native order. The new option changes scheduling only;
semantic mode configurations retain their original names. Reconstruct the
complete raw command sequence, verify source restoration and identical artifacts.
The scheduler helper must reproduce archived behavior and existing receipts.

Warm comparison: fifteen cycles of the pgrust API edit, then fifteen Nushell
cycles, each with fresh run/cache identities and the usual per-cycle source
anchor and wrong-edit control. One real API edit is repeated fifteen times;
each mode occupies each edited position five times. Keep medians of paired
wall/CPU differences and ratios, all raw samples, stages and cache histories.
Do not include qualification samples or initial cold commands in warm medians.

Cold comparison: six additional fresh-target Nushell one-cycle runs, in this
fixed order of initial mode permutations:

1. native,baseline,candidate
2. candidate,baseline,native
3. baseline,candidate,native
4. native,candidate,baseline
5. candidate,native,baseline
6. baseline,native,candidate

Every mode occupies every initial position twice. Every run also executes its
wrong edit, real API edit and independent checks; the initial original-source
command is the cold sample. Use all six within-run candidate/baseline wall ratios
for the median cold gate and report CPU separately. Do not stop early after a
favorable ratio, add extra trials to cross the threshold, or combine cold samples
from qualifications and warm runs. All runs remain separate cache histories.
Cold excludes toolchain installation, dependency fetching and prebuilt std-MIR
setup. OS caches are not cleared and other workloads remain untouched.

Only if the primary cold and warm criteria hold, check held-out Ruff, private
rg-aot and the original fre workflows with their exact corpus tests, wrong edits,
MIR options and budgets. No broad retention or large-codebase readiness claim
precedes those checks. A failed timing criterion preserves the candidate as an
experiment and chooses a different next direction; it does not justify another
round of wrapper tuning or a reset of the native-call gates.

Disk space is part of execution planning. The qualified object-reclamation tool
may remove only inventoried non-executable `.o` files from completed public
native targets after lock, provenance, live-file and artifact checks. Preserve
all other files, including executables, libraries, metadata, query caches,
bytecode snapshots and reports. Cleanup is outside command timers, documented
separately, and never touches private or unrelated work. Recheck available space
before each new large cache history; the per-command guard remains eight GiB.

Status: scheduler helper passes 48 synthetic configurations, thirteen historical
reports, nine malformed inputs, two false receipts and three early CLI rejects.
The reversed-order three-cycle pgrust qualification passes 36 commands and
18 paired artifacts. Pgrust's fifteen-cycle comparison passes 180 commands and
90 artifacts, with median paired wall/CPU reductions of 4.57%/4.46%. Nushell's
fifteen-cycle run is active (`lightweight-wrapper-nushell-repeated-01`);
six balanced cold histories remain pending.
