# Preserve completed host caches to fund further measurements

The [twenty completed host object inventories](../../../results/worker-cold-host-object-storage-01/assessment.md)
released only 1.54 GiB. Their retained files contain another 5.31 GiB of unique
inode contents. These are measured inventory totals, not predictions of archive
size or physical space recovered. Repeatedly guessing at small object targets
is not an adequate storage strategy for the remaining cold histories.

Extend the qualified cache archive selector to completed **debug workspace
checks without an installed-tool publication**. Reuse the existing bounded
snapshot, ZIP encoding, full decoded verification, reservation and exact-file
retirement mechanisms. Do not invent another archive format or erase original
test/source evidence. Restrict the first implementation to the existing
`workspace_check_evidence.py` contract and exact `.work/diagnostic-builds/<run>`
targets. Other diagnostic drivers and installed release builds remain excluded.

Represent the provenance kind explicitly and retain the interpretation of
existing workflow plans. A host preparation must have no workflow corpus or
guest mode. Derive its target from a successful terminal check with verified
archived sources, logs and test totals; reject installed-tool reports. Confirm
that every external proof lies outside the target that would be retired.
The benchmark lock already serializes host checks. Recheck terminal ownership,
all evidence, the manifest and open files before archival and again before
retirement. Keep the exact target root so the historical evidence verifier can
still check its canonical path after retirement.

Reject ambiguous selector combinations, unknown provenance kinds, unfinished
checks, mismatched targets, publication-bearing checks, changed evidence,
unexpected files and repeat application. Qualify legacy workflow selection,
inspection/restoration and the new host selector before using it. The archive
format's existing rejection and restore checks remain relevant; a new selector
does not imply that a cache will be reused by Cargo after restoration.

First prepare and review one small completed host target from the linked
twenty-check inventory. Archive it only after selector qualification, then
verify its receipt and unchanged historical check evidence. Only after that
pilot prepare a bounded batch of further exact targets, with distinct archive
reservations and a separately committed inventory review. Never launch another
lock waiter during an archive batch. Preserve every failed preparation or
application and audit its actual state before proceeding.

All maintenance occurs between measurements. Keep the worker study's eleven
frozen workflow inputs, installed tool78, sample count, mode order, tests and
numerical gates unchanged. Record actual available space before each next cold
history. The approximately 21-GiB planning target is informed by previous
11.305-GiB one-cycle caches; the eight-GiB per-command guard remains unchanged.
Do not control unrelated processes, retire private targets, or claim storage
maintenance as a compilation improvement.


Implementation `71b05ca` passes [selector qualification](../../../results/host-cache-selector-03/assessment.md)
(26 selection rejections, six CLI checks, three real host checks and four legacy
workflow modes), [archive regression checks](../../../results/cache-archive-qualification-08/assessment.md)
(44 rejections, four coordinator cases, two earlier-format restores), and eleven
batch-routing rejections. The [actual pilot](../../../results/host-cache-pilot-01/assessment.md)
now completes: 671 paths / 235.8 MB unique preserved in 85.7 MB of ZIP data, with
all 106 external hashes unchanged. Prepare a separately reviewed bounded batch
next. Failed qualification-driver runs01/02 remain recorded; no real target was
changed by those failed checks.
