# Typed native-call scope

This is a census of saved executions, not a timing measurement or a runtime change. Typed artifacts and full recorded operations matched their profiles; instruction, direct/indirect-call and local-argument totals matched the prior frame census. The exact emitter predicate/local-fill proof was compiled, with its source verified against the profile-era commit.

| Workload | Category | Executed direct calls | Share of direct calls | Share of frame bytes |
| --- | --- | ---: | ---: | ---: |
| folded | acyclic_strict_leaf | 3,866,692 | 14.92% | 4.40% |
| folded | locally_supported_with_direct_calls | 18,398,582 | 71.00% | 14.36% |
| folded | strict_leaf | 4,387,962 | 16.93% | 6.34% |
| folded | transitively_supported_with_direct_calls | 13,698,381 | 52.86% | 14.15% |
| token-phrase | acyclic_strict_leaf | 16,602,046 | 15.02% | 5.07% |
| token-phrase | locally_supported_with_direct_calls | 50,841,553 | 46.01% | 11.51% |
| token-phrase | strict_leaf | 16,615,230 | 15.04% | 5.08% |
| token-phrase | transitively_supported_with_direct_calls | 36,962,388 | 33.45% | 10.05% |

Frame bytes exclude alignment padding. Logical bytes and call counts do not measure CPU cost. Eligibility conservatively includes untaken paths; the direct-call closure may contain cycles. Acyclic bounds count virtual operations, including Return, rather than time spent inside those operations. Indirect target attribution is unavailable.

Eight diagnostic tests passed. The narrow result prompted a second census that explicitly counts terminal-Trap support and bounded nested call trees. No previous samples were replaced. [Expanded analysis](../native-call-census-02/assessment.md).

The exact first-version diagnostic sources remain in `.work/native-call-census-01/source`. The checked-in [reverse patch](from-census-02.patch) reconstructs that version from the expanded census sources with `git apply --unidiff-zero`; the original source hashes are in [summary.json](summary.json).

[Raw-result hashes and source/input manifest](summary.json)
