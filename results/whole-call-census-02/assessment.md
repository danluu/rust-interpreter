# Whole-call opportunity census

Seventeen tests pass. Both exact original artifacts and profiles reconcile every
logical/native instruction, direct Call and Return counter. No guest execution.

| Necessary eligibility condition | Folded dynamic calls | Token dynamic calls |
| --- | ---: | ---: |
| New complete-result-copy forwarders | 1,065,129 | 8,105,036 |
| Leaf blocked only by CompareBytes | 0 | 434,138 |
| Leaf blocked only by old initialization proof | 929,325 | 16,716,285 |
| Leaf blocked only by either/both of those rules | 929,325 | 25,048,737 |

Forwarders number three folded and sixteen token, with 119,294,800 and
340,580,196 dynamic frame bytes respectively. The hot token comparison leaf
requires both CompareBytes and the entry-prefix initialization proof. The
existing inliner still uses the older block-local proof. The top token
nonoverlap helper alone receives 12,046,753 direct calls.

Counts are opportunities, not speedup estimates. Other leaf limits remain;
caller placement/growth can reject otherwise eligible leaves, and expansion can
introduce register clearing. Next measure actual bounded placements and resulting
initialization requirements before selecting a compiler implementation. The
first run's test-count admission failure is preserved; no assertion was changed.
