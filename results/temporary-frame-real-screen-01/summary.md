# Scratch frame reuse: real-artifact execution screen

The candidate wins 19/24 alternating execution pairs using an identical VM. All selected original tests pass with both exports; instruction counts and native-entry counts are unchanged. These timings exclude Cargo and export, so complete edited-command comparisons remain necessary.

| Workflow | Prior median (s) | Candidate median (s) | Median paired change (ms) | Wins | Peak guest bytes before → after |
|---|---:|---:|---:|---:|---:|
| fre-folded-literal-trie | 2.7005 | 2.6796 | -25.147 | 4/6 | 95072 → 93792 |
| fre-word64 | 1.4153 | 1.4064 | -8.131 | 4/6 | 107616 → 106784 |
| fre-word64-inline8 | 0.9083 | 0.8958 | -12.090 | 6/6 | 106384 → 105648 |
| pgrust-sha1-inline8 | 0.4110 | 0.4081 | -3.006 | 5/6 | 1019760 → 1017824 |

Scratch reuse preserves every MIR local and hidden caller-location slot. Only fully initialized compiler temporaries share storage across completed MIR operations; generated Result adapters stay outside reset logic. Focused native checks pass 1,014 commands, including simultaneous constants, returned static pointers, branches/backedges, recursion and tracked caller locations.

Total frame sizes sum distinct functions, not peak live memory. Direct-call byte counts exclude alignment, argument copies and indirect calls; they are not CPU-time attribution.

All timings, native source-control reports, artifact hashes, profiler hashes and frame changes are retained in [the JSON record](summary.json). Broad correctness subsequently passed, but the [complete edited-command comparison](../paired-temporary-frame-compute-01/summary.md) did not establish consistent benefit. The change was set aside and the prior baseline restored.
