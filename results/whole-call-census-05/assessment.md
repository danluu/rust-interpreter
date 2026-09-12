# Definite-initialization and whole-call placements

Twenty-one tests pass, including an independent oracle over 38,416 small graphs,
join/backedge/alias checks and every proof resource bound. Exhaustion requires
clearing. Both real profiles reconcile exactly and the unchanged pass reproduces
the integrated library's Program byte-for-byte.

| Policy | Folded selected original calls | Token selected original calls | Added folded/token operations |
| --- | ---: | ---: | ---: |
| Unchanged second pass | 0 | 1,733,361 | 0 / 2,229 |
| CompareBytes + bounded CFG proof | 929,321 | 26,781,495 | 10,164 / 15,192 |
| Same, allowing one direct Call per body | 11,839,956 | 50,007,778 | 45,583 / 105,346 |

Neither CFG policy introduces clearing under the proposed shared runtime proof.
All existing size, ABI, frame and code-growth limits remain. The larger policy
selects 698 folded and 2,143 token static sites. This motivates one isolated
runtime/compiler candidate, with conservative recursion/indirect-closure exclusions
added before execution. No production changes or new guest executions yet.

The numbers weight original sites in already optimized artifacts. Cloned nested
calls and the exporter pipeline can change actual dynamic counts; the baseline
second pass is not a candidate gain. No percentage or latency prediction follows
from these counts. Fresh strict/native/original-assertion checks and full real-edit
comparisons determine adoption. The initial missing-type compiler failure is
preserved separately with its source and diagnostics.
