# Corrected spill partition identifies byte-wise joins

Three controls pass, including a dead-use regression, and all 245 current scalar
bodies reconstruct exactly. Every function's spill categories now sum exactly
to the live-only definition and operand totals. Census02's invalid partition is
retained separately. The larger local register-pool conclusion is unchanged.

| Successful IR occurrences | Block | Exhaustive |
| --- | ---: | ---: |
| Cross-block spilled definitions | 31,175,892 | 23,873,714 |
| Cross-block spilled operands | 84,106,644 | 23,966,788 |
| One-byte phi operands | 75,021,509 | 119,317,301 |
| Other phi operands | 43,008 | 200 |

One-byte phis include both register and memory merges. Filtering their recorded
incoming slices shows 66,410,497 block and 95,492,513 exhaustive operand uses
belong to size-one memory merges. The hot copy-precondition function contains
eight adjacent byte phis with identical predecessor/source pairs and offsets
0 through 7: one 64-bit value is split at the join and then reconstructed.
These counts exclude dead nodes and phi-edge transfers; they are not native
instruction counts or speed estimates.

Prioritize contiguous byte-phi coalescing in the scalar graph builder. Start
from the adopted runtime, so another end-to-end test isolates that graph change
without including the parked read-only/store prototypes. Group only when every
predecessor provides consecutive bytes from the same source value, bounded to
16 bytes. Preserve partial-width/high-lane semantics, original PCs, strict
checking and all resource limits. Cross-block register allocation remains a
separate larger option after this measured structural issue is addressed.
