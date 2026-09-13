# Folded matching regression guard

All154 commands pass their expected original, wrong-edit, valid-edit
and restored outcomes. The18 original selected tests remain unchanged;
baseline/duplicate/candidate bytecode and catalogs match at each state.

| Measurement | Value |
| --- | ---: |
| Paired candidate/adopted wall ratio |0.999673 |
| Paired candidate/adopted CPU ratio |1.007893 |
| Observed wall A/A |0.530% |
| Observed CPU A/A |0.440% |
| Declared wall margin |1.004975 |
| Declared CPU margin |1.012295 |
| Paired ordinary-native wall ratio |0.935909 |

The regression guard passes its predeclared1.05 wall and CPU margins. This is
not a claim of an incremental speedup on this selection. Ratios are medians
of the15 individual valid-edit pairs; observed A/A is not a confidence interval.
The complete comparison still requires Nushell and the final serialized audit.
