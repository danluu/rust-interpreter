# Hot loops in the adopted custom JIT

The closed offline census assigns all 1933 and1429 generated self-PC samples
from two retained fre test captures. It creates no guest, compiler, or timing run.
[Complete census](../results/adopted-hot-loop-census-02/summary.json) and
[independent closure](../results/adopted-hot-loop-census-02/closure.json).

| Scope | Block capture | Exhaustive capture |
| --- | ---: | ---: |
| Direct operations inside cyclic components | 503 /1933 (26.0%) | 304 /1429 (21.3%) |
| Separately associated loop-region overhead | 130 | 98 |
| Direct samples in call-free cyclic components | 35 (1.8%) | 120 (8.4%) |
| Call-free components at most128 operations | 14 | 2 |
| Direct samples in components containing calls | 468 (24.2%) | 184 (12.9%) |

There are1023 structurally reachable cyclic components in the artifact. All have
one external entry, which does not prove their nested control flow reducible.
The leading block-capture components are epsilon_closure (119 direct samples,
816 bytecode operations,2 calls), next (83,968,4), and iter_nfa_state_ids
(69,393,1). The exhaustive capture instead has substantial call-free work in
enforce_upper_bounds (63 samples,423 operations) and scan_block_masks (42,292).
The census keeps names as descriptions and uses artifact/function/PC identities.

This argues against a tiny call-free-loop extension as the primary next change.
Investigate the large ordinary-function regions that contain these loops and
calls. Copies dominate the block capture's cyclic operations (178 samples),
followed by calls102 and loads81. A bounded local-memory equality analysis could
recognize copies that write bits already present, independently of register-cache
residency; measure its scope before implementing a production pass. Unknown
writes/calls, overlap, range bounds, budgets and native exits must remain correct.
No such pass is implemented or qualified by this census.

Normal-return CFGs overapproximate possible execution. All assertions, faults and
call effects remain barriers to any future safety argument. Partial normal-entropy
sampling windows are perturbed diagnostics; fixed-entropy whole-test logical
counts are reported separately. Neither is an end-to-end speedup estimate.

All17 graph/parser controls passed, including exhaustive three-node directed
SCC graphs and independent seeded CFG reachability checks. The first census
failed on valid bare ResetThreadLocals after16 controls passed; its source/logs
and failed receipt remain retained. The first successful census's closure
recomputed both cases but rejected equivalent Homebrew Python path spellings.
A separately registered closure resolved executable paths, retained that failure,
rechecked exact arguments/hashes and recomputed both full derivations. CLOSED25261.

The failed compact-switch runtime remains parked; main runtime is unchanged.
