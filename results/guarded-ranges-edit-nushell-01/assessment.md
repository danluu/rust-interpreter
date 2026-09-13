# Nushell regression guard passes

All132 expected commands complete across14 original type-relation tests,
three changed-source cycles, deliberate wrong edits and final restoration.
Baseline/duplicate/candidate artifacts and catalogs match at every state.

| Measurement | Value |
| --- | ---: |
| Paired candidate/adopted wall | 0.988192 |
| Paired candidate/adopted CPU | 0.999165 |
| Observed wall A/A | 5.598% |
| Observed CPU A/A | 3.251% |
| Frozen wall margin | 1.044171 |
| Frozen CPU margin | 1.031672 |
| Paired ordinary-native wall | 0.618820 |

Both margins pass1.05. The favorable1.18% wall estimate is inside5.60%
observed A/A variation; this does not establish an incremental Nushell gain.
Ratios are medians of15 valid-edit pairs, and A/A is not a confidence interval.
Two Cargo workers and two prepared custom workers are unchanged; native libtest
retains its default threading. All original assertions and source bytes remain.

The continuation adds only this formerly unstarted case after disk admission.
The four completed cases were audited and retained without repeated commands.
[Complete five-case decision](../guarded-ranges-admission-resume-01/assessment.md).
