# Medium aggregate leaf inlining: runtime screen

The candidate wins 17/24 alternating execution pairs using an identical VM. Folded-trie regresses in four of six pairs; the other three cases improve in most pairs. All selected original tests pass. This screen excludes Cargo and export; complete edited-command comparisons remain necessary.

| Workflow | Prior median (s) | Candidate median (s) | Median paired change (ms) | Wins |
|---|---:|---:|---:|---:|
| fre-folded-literal-trie | 2.6898 | 2.7076 | +27.384 | 2/6 |
| fre-word64 | 1.4601 | 1.4343 | -13.992 | 6/6 |
| fre-word64-inline8 | 0.9015 | 0.8967 | -6.151 | 5/6 |
| pgrust-sha1-inline8 | 0.4097 | 0.4070 | -1.837 | 4/6 |

In folded-trie, direct calls fall from 43,586,672 to 39,809,685, while aggregate reserved frame bytes rise from 45,723,592,717 to 47,589,236,552. The two targeted Result::unwrap bodies are fully inlined at their measured call sites. Larger inline banks impose costs even on paths that skip a particular inlined call.

Direct-call frame bytes exclude argument copies, alignment, inline-bank filling and indirect calls. Counts are not causal CPU time.

The change raises the body-copy, argument and result limits together from 32 to 128 bytes. Frame, register, code-growth and diagnostic bounds remain unchanged. All 99 bytecode tests pass, including aggregate aliasing, cold failures and exact budgets. Broad native and full-command qualification are pending.

[All samples, hashes, profiles and frame changes](summary.json).

SHA-1 runs identical bytecode on the identical VM in all six pairs. Its timing differences are controls for variation, not execution-code gains. The three changed-bytecode cases win 13/18 pairs.
