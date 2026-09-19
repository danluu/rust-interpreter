# Next runtime work

The shared cold fault-tail40-command edited-source primary is closed and failed
its original wall and CPU requirements. All assertions and restoration pass;
wall1.025596964 and CPU1.014945602 establish no benefit. Park the candidate and
cancel all larger histories. The code-size reduction and correctness evidence
remain valid, but do not justify adoption or an unchanged retry.
[Decision](results/shared-cold-tail-screen-token-01/ASSESSMENT.md).

The private host-frame pairing census is closed and deferred: its two potential
memory instructions together cover only9/1,933 and9/1,429 generated samples.
No runtime prototype or timing follows. [Census](results/native-frame-access-census-01/ASSESSMENT.md).

The consumer-only upper-store proof is closed and deferred (33/13samples).
The broader logical-width census covers126/1,933 and119/1,429 generated samples,
with conservative6.54M/8.51M interpreter read repairs. Its7commands,7Rustcontrols
per profile and6trafficcontrols pass; both current profiles and retained captures
reconcile exactly. Prototype implicit-zero high words with a complete native
and interpreter read contract. Preserve stale-storage safety, initial-zero
semantics, all budgets/faults and strict checking. Main remains unchanged.
[Contract](docs/IMPLICIT-ZERO-REGISTER-DESIGN-20260918.md),
[census](results/narrow-register-storage-census-01/ASSESSMENT.md).

The previous indirect/readonly/successor composition is rejected after its
parser CPU margin failed1.05. The narrower address/budget/spill/scalar variants
remain parked under their original gates. No repeated capture or timing is
needed merely because a later evidence audit waits for the shared lock.

Compiler/Cargo/frontend and application-admission work belongs to other sessions.
Preserve their trees, processes and ownership. Root work remains custom runtime
optimization guided by real source edits; main retains adopted scratch/scalar
VM6ac4dd9e until a complete qualification admits a replacement. The goal stays
paused and manual optimization continues indefinitely.

[Archived detailed candidate history](docs/history/RUNTIME-NEXT-20260918-before-cold-tail-primary.md),
[suggestions review](docs/SUGGESTIONS-REVIEW-20260913-1245.md).
