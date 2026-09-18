All five predeclared performance guards pass across 726 complete commands. The candidate combines scratch-register memory-value reuse with the previously experimental scalar-call/private-transfer path. It uses the custom interpreter/direct AArch64 JIT and finishes Rust type and borrow checking before execution. The result does not isolate the marginal effect of the scratch cache from the scalar-call composition.

| Case | Commands | Candidate/baseline wall | Candidate/baseline CPU | Wall + A/A margin | Candidate/native wall |
|---|---:|---:|---:|---:|---:|
| token | 154 | 0.936992 | 0.934942 | 0.951120 | 1.571393 |
| folded | 154 | 0.968919 | 0.975493 | 0.983761 | 0.918104 |
| pgrust | 154 | 0.993862 | 0.994779 | 1.008860 | 0.846553 |
| rg-aot | 132 | 1.004840 | 1.008911 | 1.032169 | 0.409691 |
| nushell | 132 | 0.999955 | 1.000212 | 1.024804 | 0.636326 |

Token improves 6.30% wall and 6.51% child CPU, with a 1.41% wall A/A envelope. It remains 1.571 times ordinary native. Folded matching improves 3.11% wall. Pgrust hashfn, private rg-aot and Nushell pass regression guards; their small baseline differences establish no speedup. Nushell is effectively unchanged against the matched custom control and takes 63.63% of native wall time. These are changed-source command measurements, with 15 valid edited pairs per case. Cold, wrong-edit and restored-source commands establish correctness and are excluded from the edited timing ratios.

The independent 88-command parser histories also pass with all114 original tests: incremental wall ratio1.00545 versus the matched baseline (1.26328 versus native), and repository-default wall ratio1.00318 (1.14023 versus native). Neither establishes a parser speedup. The separate114-test compatibility run,608 workspace checks per profile,121 strict/cache commands, six exact original profiles and13 selected/prepared controls remain bound to their existing receipts.

The four closed cases were retained exactly; the last admission ran only132 new Nushell commands and repeated none of the preceding594. Nushell started above the unchanged47.03 GiB initial estimate and kept the8 GiB child floor, two Cargo workers, ordinary OS entropy, full checking and16 MiB JIT arena. No unrelated process was controlled.

The final closure verifies9,218 unique frozen inputs and119 Git source bindings, original source restoration and all retained artifacts. Exact candidate tool df4006e0 / VM6ac4dd9e uses exporter cf4b3499 and wrapper45bca4f2; the matched control is4a1381c4 / VM8f08254c. Measurements remain tied to those identities and source c88d1ead. Private details remain local.

Proceed to current-main integration and compatibility qualification. The runtime is not yet adopted; preserve main’s separate compiler-loader change and retain this measured VM exactly. The archived campaign requires its original experiment source; do not rerun completed timings.
