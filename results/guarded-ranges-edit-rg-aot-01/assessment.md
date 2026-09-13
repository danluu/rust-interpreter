# Private rg-aot regression guard

All132 commands pass their expected original, wrong-edit, valid-edit
and restored outcomes. The1 original selected tests remain unchanged;
baseline/duplicate/candidate bytecode and catalogs match at each state.

| Measurement | Value |
| --- | ---: |
| Paired candidate/adopted wall ratio |0.994551 |
| Paired candidate/adopted CPU ratio |1.000997 |
| Observed wall A/A |2.614% |
| Observed CPU A/A |2.631% |
| Declared wall margin |1.020689 |
| Declared CPU margin |1.027306 |
| Paired ordinary-native wall ratio |0.388598 |

The regression guard passes its predeclared1.05 wall and CPU margins. This is
not a claim of an incremental speedup on this selection. Ratios are medians
of the15 individual valid-edit pairs; observed A/A is not a confidence interval.
The complete comparison still requires Nushell and the final serialized audit.

Only aggregates are published. Private source, names and raw records remain local.
