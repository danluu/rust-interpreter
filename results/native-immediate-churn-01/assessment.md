# Most large body churn is immediate-value churn

The observer passed two controls and all 14 consecutive transitions across the
saved token and parser histories. Every changed function ID matches the
independent, closed full-body digest census. No guest or executable code ran.
Closure verifies 263 inputs and 18 artifacts; setup and inspection took 17.26 s.

| Genuine edit | Changed bodies | Only immediate values changed |
| --- | ---: | ---: |
| Token 1 | 2,102 | 2,087 |
| Token 2 | 14 | 0 |
| Token 3 | 14 | 0 |
| Token 4 | 2,301 | 2,300 |
| Token 5 | 2,313 | 2,299 |
| Parser 1 | 2,654 | 2,648 |
| Parser 2 | 1 | 0 |
| Parser 3 | 1 | 0 |
| Parser 4 | 4,038 | 1,815 |
| Parser 5 | 2,771 | 2,769 |

Parser edit 1 changes 9,115 immediates by +16. Token edit 4 changes 6,387 by
+112 and 5,377 by +256. Parser edit 4 also changes 682 names, 652 layouts and
640 code lengths at their numeric IDs; IDs are not uniformly stable. These
counts retain all code, including functions not executed in a selected test.

Many numeric values fit their artifacts' data ranges and address equal 16-byte
windows. This supports investigating data placement but does not establish pointer
provenance: the explicit negative control uses ordinary integers that satisfy the
same test. Never normalize arbitrary immediates or patch cached code from numeric
range tests. Constant-sensitive emission and optimizations can change more than
one machine-word immediate. A future relocatable representation would require
explicit symbolic provenance and complete code-generation dependencies.

Keep persistent native caching deferred. Its current exact-body keys lose many
potential hits on data-layout edits; safe normalization is a larger compiler/IR
change with its own runtime and validation costs. Preserve this evidence for that
work without taking over the compiler session. Next investigate scalar cross-block
register allocation, a custom-backend change with an already measured spill scope.
