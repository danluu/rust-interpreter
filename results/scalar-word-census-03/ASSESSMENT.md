# Saved scalar register-liveness census

The guarded scalar-call revision remains parked after its failed primary gate.
Its exact saved bodies contain a material amount of dead register work. A bounded
source-specific AArch64 recognizer passes nine controls and revalidates the closed
profile's independent full-byte reconstruction and original-PC accounting.

| Original test | Scalar calls | Static dead / total words | Successful-call word-execution bounds |
| --- | ---: | ---: | ---: |
| Token block boundaries | 11,227,102 | 709 / 4,887 | 733,104,348–822,018,052 |
| Token exhaustive semantics | 16,298,574 | 487 / 4,233 | 1,664,902,333–1,903,160,173 |
| Folded prefilter | 1,585,153 | 34 / 360 | 375,778 |

The hot copy_nonoverlapping precondition contributes 138–158 dead words per
successful call; most define x10, the unused upper half of a narrow value.
The analysis also finds dead upper-half packing in x14 and its temporary inputs.
Every memory access, stack adjustment and control transfer is preserved by the
candidate classification. The counts are not additive with constant folding or
other future transformations.

These bounds exclude failed private attempts and may include infeasible branch
paths. They do not measure hardware instructions, cycles or end-to-end speedups.
The scalar-body maps do not assign fake native PCs to original operations.
No host build, executable publication or guest run was needed.

The first controller stopped before tests because its capture receipt argument
was missing. The second passed eight controls and stopped on an apparent cycle:
Trap is emitted as CMP XZR,XZR; B.EQ failure, whose impossible fallthrough creates
a syntactic cycle. The third proves this branch only with a unique flag-setting
predecessor, retains all other cycles as failures, and passes all bodies. Both
failed attempts remain recorded.

Next: implement a bounded pure-register elimination pass within the custom scalar
emitter, preserve all fault, budget, profiling and Call transaction behavior, and
qualify it before the same primary edited-source screen. Keep the adopted VM as
control. Existing Cargo build admission remains unchanged.
