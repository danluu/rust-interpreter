# Park cached continuations and fixed snapshots

All forty original/wrong/valid-edit/restored commands meet their expected
outcomes, preserving twelve original tests and identical candidate/control
bytecode. The first numbered attempt failed name preflight before any command;
this second attempt is the only performance screen.

| Paired valid-edit measure | Result |
| --- | ---: |
| Candidate/baseline wall | 0.992981 |
| Candidate/baseline CPU | 0.985865 |
| Maximum individual wall A/A deviation | 4.2905% |
| Maximum individual CPU A/A deviation | 4.0324% |
| Wall ratio plus envelope | 1.035886; fails |
| CPU ratio plus envelope | 1.026190; passes |
| Candidate/ordinary native wall | 1.599526 |

The 0.70% paired wall improvement is inside observed A/A variation. It does not
establish a useful end-to-end gain or prove either component has no effect.
Keep the prototype experimental; do not rerun it unchanged or start the full
five-case history/parser guards. The adopted runtime remains df4006e0.

The paired median execution-stage difference is -12.56 ms; the block test is
-12.16 ms. The Cargo difference is -46.21 ms despite unchanged compiler bytes,
so it is not evidence of a runtime mechanism. Stage medians are not additive.
Normal entropy and the two-worker policy remain fixed. Minimum recorded free
space is 12,081,668,096 bytes.

Qualification retains 612 workspace tests/profile, 407 Python passes (22 skips),
121 strict/cache commands and three exact original profiles. Closure verifies
1,670 evidence files and 56 artifacts. Source restoration and all test assertions
pass. Next review ordinary persistent-register allocation using the retained
adopted code and profiles before choosing another runtime implementation.
