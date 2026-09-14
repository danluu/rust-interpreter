# CFG and return policies agree under the limited recognizer

Twenty-one controls pass and all four analyses reconcile their original sample
totals. Both all-register and C-return policies retain the region-linear result:
45,430 / 54,667 static candidates and 7 / 13 sampled candidates. No work-budget
declines occur. The narrower candidate sets remain subsets as required.

This is not strong evidence that actual return scratch values are all needed.
The scalar-origin recognizer treats ordinary paired stack restores and other
memory forms as unknown, making every register live before those instructions.
That prevents the C-return seed from propagating backward. Bind and model the
ordinary emitter's memory forms before using the census for a runtime decision;
preserve all memory effects, writeback, pair registers and conservative vector
state. The 611,947 / 723,699 opaque words include effects not yet modeled.

No runtime, compiler, guest or machine-code publication changes occurred.
Closure verifies 83 source/artifact bindings. [Summary](summary.json),
[closure](closure.json). Full site details remain in the hash-bound local artifact.
