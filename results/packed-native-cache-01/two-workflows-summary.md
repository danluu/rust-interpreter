# Two values in the native register cache

The isolated candidate lets x5/x6 hold two values whose upper halves are known to be zero. A full-width value still occupies both registers. It preserves the strict Rust frontend, guest bytecode, memory checks, instruction budgets, and medium-copy scratch handling. The exporter binary is identical to the retained version. All 169 bytecode tests pass.

| Actual-edit workflow | Wins vs retained | Median paired change | Execution change | Wins vs native |
| --- | ---: | ---: | ---: | ---: |
| token-phrase | 4/5 | -221.6 ms | -158.0 ms | 0/5 |
| folded-literal-trie | 5/5 | -59.0 ms | -30.9 ms | 0/5 |

| Workflow | Cold native | Cold retained | Cold candidate |
| --- | ---: | ---: | ---: |
| token-phrase | 8.107 s | 12.442 s | 12.495 s |
| folded-literal-trie | 8.308 s | 8.429 s | 7.728 s |

The artifact-only screen had 5/6 wins on token-phrase (median −71.2 ms), 6/6 on folded-trie (−25.6 ms), 6/6 on TLS (−12.8 ms), and 4/6 on SHA1 (−4.1 ms). The interpreter control had 3/6 wins and no consistent direction. Wall and child CPU times are recorded separately.

On the recorded folded trace, weighted virtual-register loads decreased from 189,948,726 to 40,291,465 and stores from 1,461,031,164 to 1,414,173,106. Generated code grew from 4,040,756 to 4,063,660 bytes. These are emitted-instruction counts, not hardware memory traffic.

The candidate remains isolated. All fourteen fresh baseline/candidate guest-artifact pairs match retained artifacts, original assertions are unchanged, deliberately incorrect edits fail at runtime, and the benchmark source is restored. Raw timings, cold costs, tool hashes, and artifact provenance are retained in summary.json.
