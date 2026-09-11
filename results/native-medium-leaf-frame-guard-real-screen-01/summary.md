# Medium aggregate leaf inlining with a frame-growth limit

Six alternating execution pairs per case use the identical VM binary. These timings exclude Cargo and export; edited-command qualification is separate.

| Workflow | Prior median (s) | Candidate median (s) | Median paired change (ms) | Wins |
|---|---:|---:|---:|---:|
| fre-folded-literal-trie | 2.7079 | 2.6611 | -55.289 | 6/6 |
| fre-word64 | 1.4205 | 1.4233 | +2.756 | 2/6 |
| fre-word64-inline8 | 0.8990 | 0.8951 | -4.145 | 5/6 |
| pgrust-sha1-inline8 | 0.4082 | 0.4064 | -1.750 | 5/6 |

The candidate wins 18/24 execution pairs. All selected original tests pass.

Newly eligible aggregate leaves must add no more than half the original caller frame, including bank alignment. Existing small-copy eligibility and all other limits remain. The threshold is an experimental cost heuristic; selection uses no runtime profile or function-name rules.

Direct-call frame bytes exclude alignment, argument copies, inline fills and indirect calls; these counts do not attribute CPU time.

[All samples, hashes, profiles and frame changes](summary.json).

SHA-1 runs identical bytecode on the identical VM in all six pairs. Its timing differences are controls for variation, not execution-code gains. The three changed-bytecode cases win 13/18 pairs.
