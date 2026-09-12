# Saved folded programs: correctness coverage and runtime diagnosis

All 34 original tests pass across 21 VM commands and three exact whole-artifact
verifications. The VM bytes are identical. Each case replays one recorded random
stream across three alternating pairs; entropy request lengths, counts and bytes
match exactly. Per-test peak memory matches; each artifact has stable instruction
counts across repeats. Saved artifacts and original native receipts remain unchanged.

| Case | Tests | Runtime wall change | Runtime CPU change | Logical instruction change |
| --- | ---: | ---: | ---: | ---: |
| token | 12 | -2.63% | -2.63% | -4.90% |
| folded | 18 | -0.91% | -0.85% | -10.69% |
| pgrust | 4 | -10.11% | -10.53% | -16.51% |

These are runtime diagnostics, conditional on one entropy stream per case.
Pgrust commands are about 20 ms and absolute savings are small. Token saves
about 0.17 seconds, while the earlier offline transform took about 0.32 seconds.
Those separate observations suggest a poor standalone full-workflow prospect;
they are not a measured edit/build/test ratio. Token screen01 stopped before
any Cargo or guest child because free disk fell below its 6.5 GiB admission.

Subsequent boundary review found that the old folder could replace a faulting
null load with readable padding data. The two new regressions failed on the old
analyses and passed after both analyses rejected address zero. Thus this replay
qualifies coverage of the selected real tests, not the old optimizer generally.
The old composed tool is disqualified for adoption; its source fix and new tool
qualification must precede any real performance screen.
