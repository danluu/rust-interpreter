# Diagnose cached native continuations and transition bookkeeping

The branch-selected-address composition failed its primary wall gate and is
parked. Main retains the adopted VM. Saved native Return dispatch accounts for
35/1651 and31/1439 generated samples; callee target lookup covers only9/13.
Do not assume an entire bucket can be removed or add a new table without evidence.

Reconstruct both saved adopted captures byte-for-byte in a test-only observer.
For every compiled Call, inspect the existing internal resume entry at next PC;
convert its instruction index to a byte offset, then record eligibility and the immediate/store instruction
cost of a prospective cached32-bit offset. Distinguish an unsupported continuation
and the one-past-code entry. The proposed offset could occupy existing frame
padding, but the diagnostic never reads padding as data or changes Frame.

Join exact typed sites to the three-vector validated original logical profiles.
Keep ordinary-entropy sample windows distinct from entropy-bound execution counts.
Count missing executed functions explicitly. Native calls and returns differ:
frames entered by the VM must retain the existing return-lookup fallback.

Refine the exact saved native protocol spans to find the three-word cursor call
and return counter updates. Count actual sampled PCs and weighted emitted words,
not an inferred retired-instruction saving. Preserving counters in caller-saved
SIMD registers is only a hypothesis; every VM exit/reentry and floating/copy/ABI
clobber contract would require qualification before any implementation.

Two new tests check internal targets/unsupported tails and the proposed separate
layout type. Expect414 bytecode tests per debug/release profile (10 ignored
across the package). No exporter source changes or exporter retest is required.
Use the shared lock,45-second admission, two Cargo workers,12GiB build admission
and8GiB child floors. No guest execution, native code publication, runtime change
or new performance screen in this diagnostic. Preserve peers and paused goal.

The first debug run caught that instruction/byte unit mismatch in the new
diagnostic. Its271 passing library tests and one failing diagnostic remain
recorded; no census or release run occurred. Correct the observer and repeat
qualification under a fresh build ID. Production emission remains unchanged.
