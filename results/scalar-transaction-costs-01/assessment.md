# Repeated store work is large enough for another implementation

The observer exactly reconstructs all 245 scalar bodies in the three candidate
profiles and passes both structural controls. No guest executes and no native
code is published. Closure verifies 258 source/retained bindings and all logs.

| Successful-path count | Token block | Token exhaustive | Folded |
| --- | ---: | ---: | ---: |
| Store-bearing native Calls | 8,696,001 | 16,803 | 1 |
| External stores | 60,011,137 | 115,684 | 1 |
| Same-block containing prior write | 32,936,960 | 64,670 | 0 |
| Later same-block complete overwrite | 32,936,960 | 64,670 | 0 |
| Unneeded high value lane | 60,001,281 | 115,658 | 1 |
| Unused logical-address snapshot | 50,028,481 | 98,039 | 1 |

SipHash rounds contribute all 32,936,960 block check-reuse opportunities across
3,293,696 successful Calls. Sparse-set updates contribute 10,332,672 stores,
with no same-block check reuse. Counts overlap and omit private failed attempts;
they are not latency estimates.

Next implement bounded store-log simplification: reuse a prior checked write's
containing host range within one basic block, omit earlier stores completely
overwritten later in that block from the final commit, and omit provably unused
snapshot lanes. Private reads still observe every original store in order;
private failures still replay all original effects. Keep the failed candidate
parked and independently qualify the new emitted code before another screen.
