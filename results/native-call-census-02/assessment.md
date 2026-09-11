# Typed native-call scope

This is a census of saved executions, not a timing measurement or a runtime change. Typed artifacts and full recorded operations matched their profiles; instruction, direct/indirect-call and local-argument totals matched the prior frame census. The exact emitter predicate/local-fill proof was compiled, with its source verified against the profile-era commit.

| Workload | Category | Executed direct calls | Share of direct calls | Share of frame bytes |
| --- | --- | ---: | ---: | ---: |
| folded | acyclic_strict_leaf | 3,866,692 | 14.92% | 4.40% |
| folded | locally_supported_with_direct_calls | 18,398,582 | 71.00% | 14.36% |
| folded | prospective_acyclic_leaf_with_terminal_traps | 5,590,552 | 21.57% | 9.97% |
| folded | prospective_bounded_call_tree_with_terminal_traps | 14,151,386 | 54.61% | 17.55% |
| folded | prospective_direct_call_closure_with_terminal_traps | 15,436,512 | 59.57% | 19.73% |
| folded | prospective_leaf_with_terminal_traps | 6,113,505 | 23.59% | 11.91% |
| folded | strict_leaf | 4,387,962 | 16.93% | 6.34% |
| folded | transitively_supported_with_direct_calls | 13,698,381 | 52.86% | 14.15% |
| token-phrase | acyclic_strict_leaf | 16,602,046 | 15.02% | 5.07% |
| token-phrase | locally_supported_with_direct_calls | 50,841,553 | 46.01% | 11.51% |
| token-phrase | prospective_acyclic_leaf_with_terminal_traps | 36,271,335 | 32.82% | 24.66% |
| token-phrase | prospective_bounded_call_tree_with_terminal_traps | 89,194,384 | 80.72% | 59.02% |
| token-phrase | prospective_direct_call_closure_with_terminal_traps | 89,844,169 | 81.30% | 61.19% |
| token-phrase | prospective_leaf_with_terminal_traps | 36,374,404 | 32.92% | 24.93% |
| token-phrase | strict_leaf | 16,615,230 | 15.04% | 5.08% |
| token-phrase | transitively_supported_with_direct_calls | 36,962,388 | 33.45% | 10.05% |

Frame bytes exclude alignment padding. Logical bytes and call counts do not measure CPU cost. Eligibility conservatively includes untaken paths; the direct-call closure may contain cycles. Acyclic bounds count virtual operations, including Return, rather than time spent inside those operations. Indirect target attribution is unavailable.

The prospective categories require new native terminal-Trap and Call/Return handling. They do not drop traps from execution or claim that the existing emitter supports them. Whole-call-tree bounds reject CFG cycles, recursive call graphs and overflow; each static call site is charged, including repeated calls to the same function. Every target must also be prepared and all storage ready before such a tree can run without a partial continuation.

Nine diagnostic tests passed, including duplicate display names, repeated call sites, recursive call rejection, CFG cycles, missing terminators, the actual local-fill proof and argument-source proof checks. The earlier narrower census passed eight tests and is retained separately.

The bounded-tree category covers 80.72% of token calls and 59.02% of its frame bytes; folded covers 54.61% and 17.55%. Every observed eligible call has a conservative tree bound below 8,192 instructions. This is enough scope to select the [bounded native-call experiment](../../benchmarks/experiments/bounded-native-calls/PLAN.md); no performance gain is established.

[Raw-result hashes and source/input manifest](summary.json)
