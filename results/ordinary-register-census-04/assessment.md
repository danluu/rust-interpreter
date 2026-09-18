# Memory effects expose modest ordinary-register savings

Thirty controls pass, including a separate host assembler oracle for fourteen
integer memory instructions. The assembler object is inspected as data; it is
neither linked nor executed. All memory operations remain effects, including
paired registers and base writeback. Unsupported encodings remain barriers.

| Capture | Return contract | Static unused words | Sampled unused words | Generated samples |
| --- | --- | ---: | ---: | ---: |
| Block | All registers | 49,842 | 8 | 1,561 |
| Block | C return | 60,631 | 26 | 1,561 |
| Exhaustive | All registers | 59,900 | 13 | 1,231 |
| Exhaustive | C return | 73,699 | 18 | 1,231 |

The recognizer now models 2,790,417 / 3,396,086 ordinary words, leaving
35,556 / 41,308 opaque words. Every narrower candidate remains a candidate;
both captures reconcile completely, without ambiguous samples or work-budget
declines. The C-return policy can now propagate through reviewed stack restores.

Even this wider model identifies only 1.67% / 1.46% of saved generated-code
self samples. Those partial, perturbed windows do not measure retired
instructions or establish a speedup. Defer a production register-elimination
pass; review the larger remaining native Return costs using existing evidence.
No guest, compiler, runtime or executable-code publication changes occurred.

Closure verifies 90 frozen bindings, all control logs and full site details,
plus the assembler identity and independent object. [Summary](summary.json),
[closure](closure.json).
