# Contiguous byte phis from the adopted runtime

The corrected saved-body census identifies size-one memory phi operand traffic
of 66.41 million occurrences in token block and 95.49 million in exhaustive.
The hot copy-precondition function splits a 64-bit merged value into eight byte
phis and reconstructs it afterward. Counts are diagnostic, not speed estimates.

Start from main's adopted df4006e0 runtime. Preserve ordinary admission; do not
include the parked read-only/store prototypes. When merging virtual frame bytes,
group at most 16 bytes only if every predecessor supplies consecutive bytes from
one value. Different predecessors may start at different source offsets. Stop
at any source/order discontinuity or 16-byte source boundary. Retain exact
slices and result widths, charge the additional bounded comparisons, and keep
all original PCs, budgets and strict validation.

Freeze 348 expected bytecode tests per profile (11 ignored): existing controls
plus exhaustive width/offset/budget model comparisons, a discontinuous-source
regression, and four native emission variants including the private Call ABI.
Then qualify an immutable candidate with the current compiler, strict checking,
original profiles and the unchanged 40-command changed-source primary. Larger
histories require that primary to pass. No repeated timing of parked tools.

Use the global lock, two Cargo/test workers, protected same-source ROOT target,
max(14 GiB, 8 GiB + twice allocated target) build admission and 8 GiB child floor.
Preserve exact source and evidence, private/peer work, and the paused goal.
