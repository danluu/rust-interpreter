# Guarded indirect-call comparison completed

All462 original/wrong/edit/restored commands pass,154 per case. The candidate
remains experimental; it did not establish a useful component improvement.

| Case | Paired wall change | Paired CPU change | Wall A/A | CPU A/A |
| --- | ---: | ---: | ---: | ---: |
| Token,12 tests | −1.44% | −0.97% | 4.75% | 3.28% |
| Folded trie | −0.59% | +0.48% | 10.39% | 4.06% |
| Pgrust | +0.53% | +0.37% | 1.16% | 1.08% |

Token misses the component gate. Its full stack gains12.44% wall against the
fixed anchor but still takes1.768× ordinary native. Folded misses the wall
guard under both recorded rules. Pgrust passes the documented wall/CPU margin
but fails the executable extra CPU ceiling; before either held-out ran we
required both rules to pass, so this is a failed conservative guard. The
next harness corrects this discrepancy and tests its boundaries.

The completed token run is not retimed. Its earlier52-command storage failure,
folded zero-command lock timeout and guard-controller zero-command disk failure
remain recorded. Recovery verified terminal receipts and all126 frozen inputs
before starting only the unfinished guards. Sources are restored.

Reducing interpreted indirect calls by over1.0million and0.7million in the two
dominant tests did not produce a command gain above observed variation. Keep
this implementation for reference. The next independent candidate reduces
emitted instructions for existing register transfers on the wide-operation
base, with no indirect-call specialization or compiler change.
