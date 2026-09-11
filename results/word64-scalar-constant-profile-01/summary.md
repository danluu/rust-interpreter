# Word64 profile after scalar constant lowering

Instrumented execution of the final production-edit artifact. Profile elapsed time is not a performance measurement; paired execution and full edit/build/test comparisons are recorded separately.

| Operation remaining in the VM | Count |
|---|---:|
| Return | 39,144,084 |
| Call | 39,144,083 |
| Jump | 25,822,090 |
| Local | 15,018,145 |
| Copy | 6,869,823 |
| Assert | 6,286,955 |
| Store | 3,847,958 |
| Div | 3,443,660 |
| Imm | 2,366,736 |
| Switch | 1,183,340 |
| Sub | 1,183,201 |
| Rem | 920,367 |
| Load | 587,281 |
| Unary | 324,264 |
| Allocate | 162,132 |
| Deallocate | 162,132 |
| CompareBytes | 28 |

The guest executes 3.336 billion virtual instructions, down from 3.460 billion. Generated code is 751,752 bytes, down from 790,392. The JIT compiles regions with at least three operations: after storage removal, some Sub+Imm sequences before Div and some constant Imm+Switch sequences now remain interpreted.

Checked native Div/Rem is the next experiment. It can absorb 4.36 million arithmetic operations and join nearby short sequences. Zero divisors and signed MIN/-1 must retain their existing VM errors, and instruction limits and fault ordering must remain correct.

[Qualified constant change and paired runtime](../scalar-constant-validation-01.json), [seven production workflows](../e2e-scalar-constant-corpus-01/summary.md).
