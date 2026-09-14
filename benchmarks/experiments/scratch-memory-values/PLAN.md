# Shared local scratch values

Base: qualified private-transfer runtime plus test-only scalar memory/Copy census
observers. The adopted VM remains the end-to-end control; no parked runtime has
been adopted. The same two current-VM captures identify 45/29 Copy data-load
samples and at most 45/15 Load samples with an available x9 value. These partial
samples justify an experiment, not an expected timing improvement.

Track at most 16 exact eight-byte active-frame ranges whose contents equal x9.
Use fixed host-side metadata and no additional native registers. Query only
after the existing address checks/formation, immediately before a non-forwarded
Load or Copy load. Substitute the existing x9 bits only. Retain all stores,
result high-half zeroing, budgets, logical profile accounting and fault behavior.

The existing typed memory effects invalidate overlapping/unknown writes.
Every emitted possible x9 clobber, unknown word and control transfer invalidates
all snapshots. Constant/local virtual-register definitions alone do not change
the saved bits. Capture only after real value materialization and its associated
guest-memory operation. A skipped load can retain further exact aliases, subject
to the same write invalidation. The cache resets at native region boundaries.

First run four focused controls in debug/release: fixed capacity and alias rules,
reviewed instruction classes, exact three-word reduction in a Copy/Load chain,
and interpreter/native comparisons covering overlapping writes, clobbers,
unknown pointers, faults, budgets, profiles, memory peaks, persistent registers,
resumable mode and disabled native capacity. Then complete workspace/strict
checking, exact original profiles and the unchanged primary-first benchmark.
No full comparisons unless the original primary passes.

Use the shared target from this source root, two Cargo workers, canonical lock,
14 GiB / max(8 GiB + twice allocated target) admission and 8 GiB child floors.
Keep the paused goal, peer compiler ownership, original artifacts and all prior
failed results intact. No guest compiler/interpreter fallback or relaxed checks.
