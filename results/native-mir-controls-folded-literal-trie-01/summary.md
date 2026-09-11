# Native MIR policy control

Three modes run the same five production edits and original tests. A separate wrong edit fails in the selected tests in all modes. JIT bytecode for all seven source states exactly matches retained 106eef.

| Mode | Median edit command (s) | Cold command (s) |
|---|---:|---:|
| native | 1.649 | 7.297 |
| native-mir | 1.642 | 8.950 |
| jit | 2.824 | 7.399 |

Comparisons use medians of paired after-minus-before command times:

| Before | After | Paired change (ms) | After wins |
|---|---|---:|---:|
| native | native-mir | -23.4 | 3/5 |
| native | jit | +1183.5 | 0/5 |
| native-mir | jit | +1198.7 | 0/5 |

Native MIR uses the exact target MIR level and inlining thresholds used by the JIT, with an explicit host target. Cargo test profiles are unchanged. Native retains its prebuilt standard library and libtest; the custom engine uses metadata std and direct test-entry dispatch.
This matches target MIR policy, not the whole build graph or the best possible native configuration. Cold samples use empty independent per-mode Cargo targets, with tools and std-MIR prepared beforehand. They do not reset filesystem caches. Five paired edits and one cold observation per mode limit conclusions.
Every native executable and JIT artifact is snapshotted outside the command timer. All source pins and test assertions are restored; raw commands, flags, results and hashes remain in the adjacent JSON report.
