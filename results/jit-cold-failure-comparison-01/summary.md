# Cold JIT fault formatter: rejected experiment

Moving fault-message construction to a cold, non-inlined helper preserves all 58 bytecode tests, but does not resolve the interpretation regression. This candidate was removed before testing a separate interpreter/JIT loop specialization. Every timing below compares identical bytecode against the last qualified TypeId VM; it is not a direct simultaneous comparison with the preceding assertion candidate.

| Engine / workload | Qualified VM | Cold formatter | Candidate pair wins |
|---|---:|---:|---:|
| Interpreter / word64-default | 15.920 s | 16.278 s | 0/3 |
| Interpreter / sha1-inline8 | 5.235 s | 5.139 s | 1/3 |
| JIT / word64-default | 2.313 s | 2.383 s | 1/5 |
| JIT / word64-inline8 | 1.585 s | 1.565 s | 4/5 |
| JIT / sha1-inline8 | 0.696 s | 0.681 s | 5/5 |

Word64 interpretation remains roughly 2% slower and loses all three pairs. Default-threshold word64 JIT is roughly 3% slower and loses four of five. SHA-1 interpretation is mixed: the group median is lower, but only one paired comparison wins. These results do not justify retaining the helper. Full native/launcher/production qualification was not run for this rejected candidate.

[Raw comparison records and validation](../jit-cold-failure-validation-01.json).
