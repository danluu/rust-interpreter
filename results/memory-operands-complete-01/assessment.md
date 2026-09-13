# Memory operands: useful token gain, mandatory CPU guard missed

All462 commands pass their expected outcomes. Original tests, wrong-edit
rejection, compiled restoration and bytecode/catalog equivalence pass. All432
harness inputs and6393 unique case inputs still match their frozen hashes.
The controller is terminal. **Overall adoption does not pass.** Do not retime
this completed candidate or import its runtime under a relabeled gate.

| Case | Wall vs wide | CPU vs wide | Wall A/A | CPU A/A | Guard |
| --- | ---: | ---: | ---: | ---: | --- |
| Token | −6.60% | −5.93% | 1.82% | 0.53% | Pass |
| Folded | +0.16% | −0.00% | 1.30% | 0.90% | Pass |
| Pgrust | +0.48% | +0.22% | 3.04% | 3.36% | Fail |

Token's full stack improves wall17.82% and CPU18.07% against the fixed anchor.
Its median complete command is4.503s versus4.803s for the wide control; VM
execution stages are3.000s versus3.317s. These are separate nested medians,
not an additive decomposition. The paired candidate/ordinary-native wall
ratio remains1.862. Both dominant token tests stay in the twelve-test suite.

The pgrust guard uses the worse ratio against wide and the fixed anchor,
then adds the corresponding descriptive A/A envelope. CPU is1.020271 against
the anchor; adding0.033615 gives1.053886, beyond the frozen1.05 limit. Wall
passes narrowly at1.049614. This engineering rule is not a confidence interval
and does not establish a statistically significant slowdown. It still fails
the prospectively declared adoption condition. Folded passes both margins.

The runtime passes428 Rust checks per profile,131 harness checks,7 exact
tests,9 suite commands,203 native/cache checks and3 per-PC profile comparisons.
The memory change preserves checks and full VM-register writes, removes unused
temporaries, and folds proven local offsets into hardware memory operands.
The profiles have identical logical work and5.1–5.6% smaller generated code.
The paired-register and guarded-indirect additions are excluded.

Retain this useful component for a distinct prospective composition. The next
candidate combines it with the qualified compiler-identity lookup cache,
which previously improved pgrust but failed its own broader noise guards.
That targets frontend overhead in the current pgrust guard. Neither old result
becomes a pass, and their historical ratios will not be multiplied. The new
composition must be qualified and measured together, including large/private
frontend cases. No further emitter tweak is being used to chase this result.

[Token](../memory-operands-edit-token-01/stage-assessment.md),
[folded](../memory-operands-edit-folded-01/stage-assessment.md),
[pgrust](../memory-operands-edit-pgrust-01/stage-assessment.md),
[conditional integration scope](../../docs/MEMORY-OPERANDS-INTEGRATION.md).
