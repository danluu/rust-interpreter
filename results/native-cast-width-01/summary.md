# Known-zero high halves of native casts

The isolated candidate preserves known-zero upper halves of native cast results in the existing two-value register cache. Masking, sign extension, native ABI behavior, guest bytecode, and the strict frontend are unchanged. The exporter binary is identical to the retained version. All 170 bytecode tests pass.

| Actual-edit workflow | Wins vs retained | Median paired change | Execution change | Wins vs native |
| --- | ---: | ---: | ---: | ---: |
| token-phrase | 3/5 | -42.7 ms | -48.0 ms | 0/5 |
| folded-literal-trie | 4/5 | -23.5 ms | -29.5 ms | 0/5 |

| Workflow | Cold native | Cold retained | Cold candidate |
| --- | ---: | ---: | ---: |
| token-phrase | 8.029 s | 11.517 s | 11.887 s |
| folded-literal-trie | 7.569 s | 7.383 s | 7.383 s |

The artifact-only screen had 4/6 wins on token-phrase (median −22.4 ms), 6/6 on folded-trie (−16.6 ms), 3/6 on TLS (+0.9 ms), and 4/6 on SHA1 (−2.8 ms). The interpreter control had 5/6 wins (−6.1 ms), so no emitter-specific interpretation is assigned to that control. Wall and child CPU times are recorded separately.

The typed compile-only observation and raw traffic counts are retained in summary.json. These are emitted-instruction counts weighted by a recorded workload, not hardware memory traffic or a timing result.

The candidate remains isolated. All fourteen fresh baseline/candidate guest-artifact pairs match retained artifacts, original assertions are unchanged, deliberately incorrect edits fail at runtime, and the benchmark source is restored. Raw timings, cold costs, tool hashes, and artifact provenance are retained in summary.json.

Decision: Keep isolated without integration. The two real-edit workflows have small paired median savings, mixed command wins, worse marginal medians, and a slower token cold sample. The recorded folded workload has unchanged virtual-register load count and 10,283,592 additional stores. Prioritize combining the larger MIR scalar-promotion improvement with retained packed-cache code; these results do not prove casts are universally slower.

The 170 bytecode tests passed. Broader native, TLS, and full fre qualification was not run for this version. Original benchmark samples and the slower cold token result remain preserved.
