# Defer within-span dead-temporary elimination

All sixteen controls pass, including 1,000 independent dependency-graph oracle
cases. Both current saved captures reconcile exactly; independent closure
recomputed both complete derivations. No compiler or guest was run.

| Capture | Pure overwritten words | Generated self samples on those words | All generated self samples |
| --- | ---: | ---: | ---: |
| Block | 22,346 | 4 | 1,933 |
| Exhaustive | 27,009 | 8 | 1,429 |

All twelve affected samples are in Cast operations. Most static opportunities
are also Cast temporaries. There are no ambiguous collapsed samples in this
join. These short perturbed windows cover only 0.21% and 0.56% at candidate
words, so this conservative scope does not justify a runtime pass or timing
campaign. Static word totals alone would have overstated the opportunity.

This is deliberately limited: every mapped span exit makes all registers live,
every branch and unknown instruction is a barrier, and whole scalar bodies are
excluded. There are 611,647/723,311 unknown barrier words, including ordinary
encodings outside the reused scalar decoder. These results do not bound a more
general optimizer or prove that excluded instructions are necessary. They do
preserve all memory accesses, stack effects, control flow and existing checks.

Keep the production runtime unchanged. The older scalar-callee elimination,
direct-operand and width experiments retain their prior performance decisions.
