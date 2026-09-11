# Direct dispatch after native exits: runtime direction screen

The custom VM now checks the remaining budget and dispatches the interpreted continuation immediately after a successful native exit. Generated successors already link to available native regions; a VM return leaves an unsupported or short region, a budget tail, or a missing terminator. The previous loop repeated its header and JIT lookup before that same interpreted operation.

All 107 bytecode tests pass. A first direct-entry fixture incorrectly expected success below the JIT API minimum budget; it was corrected to assert the existing no-progress rejection and zero profile hits. Missing-terminator budget ordering was also tested. Both actual runtime binaries remained identical across this test-only correction.

The candidate wins **23/24** timed pairs on four retained real test artifacts. These are VM command timings including load, validation, JIT construction and test execution. They exclude Cargo/checking/export; complete production-edit commands are still required.

| Workflow | Prior VM median (s) | New VM median (s) | Paired change (ms) | Wins |
|---|---:|---:|---:|---:|
| fre-folded-literal-trie | 2.607 | 2.490 | -124.404 | 5/6 |
| fre-word64 | 1.415 | 1.347 | -69.227 | 6/6 |
| fre-word64-inline8 | 0.895 | 0.868 | -26.944 | 6/6 |
| pgrust-sha1-inline8 | 0.391 | 0.386 | -5.405 | 6/6 |

Every compared artifact is byte-for-byte identical. Guest instruction totals, peak memory, generated-code bytes and operations, native instruction totals and JIT entries match. Separately captured complete per-PC profiles also match. The source change removes repeated host dispatch checks while preserving the measured guest work. The single losing pair and every timing are retained; no A/A correction or outlier removal is applied.

Both actual VM and exporter binaries differ from the population-count baseline. This runtime screen uses retained bytecode and does not time either exporter. The upcoming full-command comparison must use both actual tool builds and recheck emitted-artifact identity.

[Raw timings and hashes](summary.json), [prior twelve-workflow baseline](../paired-native-popcount-corpus-01/summary.md).
