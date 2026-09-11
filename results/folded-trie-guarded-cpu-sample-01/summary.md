# Folded-trie execution: guarded inliner CPU sample

A separate diagnostic execution of the original eighteen-test folded-trie workflow still spends substantial sampled CPU time in frame setup and copying. The VM exits successfully. Its instrumented wall time is excluded from performance comparisons.

| Disjoint stack category | Samples | Share of 852 samples |
|---|---:|---:|
| Generated AArch64 code | 415 | 48.7% |
| Dispatcher self | 178 | 20.9% |
| Frame reservation, including clearing | 149 | 17.5% |
| Copy path beneath dispatcher +5608 | 63 | 7.4% |
| Other runtime copy paths | 40 | 4.7% |
| Arithmetic helpers | 7 | 0.8% |

All unknown program counters counted as generated code fall within the executable mapping captured from this same owned process. The categories partition the 852 samples; no inclusive stack counts are added twice. The frame-reservation category contains 117 clearing samples, including 110 in memset.

The copy path at dispatcher offset +5608 is consistent with the direct-call argument-copy code. This is an inference from the sampled stack and current source, not a per-function timing measurement. The separate instruction profile records 39.8 million direct calls, including 2.13 million calls through a four-operation forwarding wrapper and 1.51 million calls to one empty unit-returning drop body.

These observations support testing call simplification and cheaper frame setup. They do not predict the speedup: removing calls may change generated-code behavior, memory use and compiler cost. One short sample is insufficient to generalize across projects. The guarded build still requires stronger complete-command evidence before claiming a broad performance gain.

[Complete edited-command corpus](../paired-native-medium-leaf-frame-guard-corpus-01/summary.md). Raw sample, memory map, process-identity checks and hashes are recorded in summary.json. No unrelated process was signaled or interrupted.
