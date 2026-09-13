# Pgrust regression guard

All154 commands pass their expected original, wrong-edit, valid-edit
and restored outcomes. The4 original selected tests remain unchanged;
baseline/duplicate/candidate bytecode and catalogs match at each state.

| Measurement | Value |
| --- | ---: |
| Paired candidate/adopted wall ratio |0.999250 |
| Paired candidate/adopted CPU ratio |1.001410 |
| Observed wall A/A |0.813% |
| Observed CPU A/A |0.757% |
| Declared wall margin |1.007382 |
| Declared CPU margin |1.008984 |
| Paired ordinary-native wall ratio |0.830567 |

The regression guard passes its predeclared1.05 wall and CPU margins. This is
not a claim of an incremental speedup on this selection. Ratios are medians
of the15 individual valid-edit pairs; observed A/A is not a confidence interval.
The complete comparison still requires Nushell and the final serialized audit.
