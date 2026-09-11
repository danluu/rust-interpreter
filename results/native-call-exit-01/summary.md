# Direct callee return transition

Keep retained106eef. The fast transition is correct in the focused checks, but its small isolated gains do not give a useful complete-command improvement: only6/15 edited commands beat the parent. Folded trie regresses21ms paired, TLS is effectively flat (+1.5ms), and SHA-1 saves8.4ms. The change leaves all native entries and logical instructions unchanged. Archive the extra VM control flow and investigate generated memory operations before adding a more complex native call ABI.

The isolated VM reserves and initializes the same frame/register storage, copies arguments in the same order and performs the same depth/memory checks. It runs a direct callee before pushing its guest frame. A completed native Return uses the existing result copy and truncation; other continuations restore the normal callee frame and PC.

All151 bytecode tests pass, including eight new boundary tests. A separately compiled retained implementation exactly matches all504 focused inputs: errors, normal/profiled execution statistics and complete profiles. The original folded workload also has identical complete per-PC profiles and statistics, excluding JIT compilation timing.

Six alternating same-artifact runtime pairs per case:

| Case | Engine | Baseline / candidate median (s) | Paired change (ms) | Wins |
|---|---|---:|---:|---:|
| folded | jit | 1.924 / 1.918 | -13.3 | 4/6 |
| sha1 | jit | 0.373 / 0.371 | -2.0 | 6/6 |
| tls | jit | 0.274 / 0.273 | -2.5 | 5/6 |
| pgrust-interpreter | interpreter | 0.345 / 0.324 | -22.6 | 6/6 |

The interpreter control improves even though this fast path cannot execute there. A fresh baseline binary exactly matches the retained binary, ruling out a stale baseline build; the interpreter change may reflect host code generation/layout, but its cause is unresolved. It is a single runtime control, not a qualified interpreter improvement.

Five real production edits per workflow; original assertions and the deliberate wrong edit are retained:

| Workflow | Native / baseline / candidate median command (s) | Paired command change (ms) | Execution change (ms) | Wins vs baseline / native |
|---|---:|---:|---:|---:|
| [folded-literal-trie](../paired-native-call-exit-folded-literal-trie-01/summary.md) | 1.706 / 2.809 / 2.841 | +20.6 | +6.4 | 1/5 / 0/5 |
| [forward-anchored-tls](../paired-native-call-exit-forward-anchored-tls-01/summary.md) | 1.783 / 1.341 / 1.370 | +1.5 | -3.1 | 1/5 / 5/5 |
| [pgrust-sha1-inline8](../paired-native-call-exit-pgrust-sha1-inline8-01/summary.md) | 0.781 / 0.906 / 0.901 | -8.4 | -3.8 | 4/5 / 2/5 |

The candidate wins6/15 edited commands against the retained VM and7/15 against standard native Cargo. Those native wins include noisy samples and do not establish a new native advantage. Independent medians and paired changes need not agree. Five paired edits per case limit conclusions.

| Workflow | Native / baseline / candidate cold command (s) |
|---|---:|
| folded-literal-trie | 7.081 / 7.110 / 7.538 |
| forward-anchored-tls | 7.273 / 5.964 / 5.902 |
| pgrust-sha1-inline8 | 1.198 / 1.002 / 0.914 |

Cold runs use empty per-mode Cargo targets with tools and std-MIR prepared beforehand; filesystem caches are not reset. All21 paired artifacts are byte-identical and match the retained cohort. Both modes use the identical exporter and MIR settings. Source files are restored.

The experiment was not integrated. Full fresh fre coverage and the broader multi-project qualification were not run for this candidate after the weak complete-command screen. The qualified scalar-frame build remains106eef. All failed fixture checks, exact oracle records, runtime samples, bytecode, sources and immutable tools are preserved.
