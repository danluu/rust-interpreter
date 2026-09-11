# Two values in the native register cache

The retained experimental build lets x5/x6 hold two values with known-zero upper halves, or one full-width value. Guest bytecode, the exporter binary, strict frontend checks, memory checks, instruction budgets, and the native ABI are preserved. All 169 bytecode tests, 47,004 fresh native differential commands, 245 TLS checks, and two controlled-input trace comparisons pass. All 382 non-ignored fre bodies pass against 382 fresh native executions at the explicit 150,000 allocation limit; seven remain ignored. All 70 retained commands across pgrust, Nushell, Ruff and private rg-aot preserve original outcomes. Those additional project commands reuse historical native controls and are behavior coverage. Both measured binaries reproduce exactly from a fresh source copy and build.

| Actual-edit workflow | Wins vs retained | Median paired change | Execution change | Wins vs native |
| --- | ---: | ---: | ---: | ---: |
| token-phrase | 4/5 | -221.6 ms | -158.0 ms | 0/5 |
| folded-literal-trie | 5/5 | -59.0 ms | -30.9 ms | 0/5 |
| pgrust-sha1-inline8 | 2/5 | +1.4 ms | -9.8 ms | 0/5 |
| forward-anchored-tls | 4/5 | -21.5 ms | -6.1 ms | 5/5 |

| Workflow | Cold native | Cold retained | Cold candidate |
| --- | ---: | ---: | ---: |
| token-phrase | 8.107 s | 12.442 s | 12.495 s |
| folded-literal-trie | 8.308 s | 8.429 s | 7.728 s |
| pgrust-sha1-inline8 | 1.185 s | 0.944 s | 0.831 s |
| forward-anchored-tls | 8.317 s | 6.669 s | 5.828 s |

Across these four workflows, 15/20 complete commands and 20/20 execution stages improve against retained, while 5/20 complete commands beat native Cargo. SHA1 has no meaningful whole-command improvement. Native Cargo remains much faster on token-phrase and folded-trie.

All 28 fresh guest-artifact pairs match retained artifacts. Original assertions and runtime wrong-edit rejections pass, and the source is restored. Every cold and edited-command sample remains in the raw reports. Component medians need not add to the median command difference.

The separate artifact-only screen improved 5/6 token pairs (−71.2 ms), 6/6 folded pairs (−25.6 ms), 6/6 TLS pairs (−12.8 ms), and 4/6 SHA1 pairs (−4.1 ms). The interpreter control had 3/6 wins. On the recorded folded trace, weighted virtual-register loads decrease by 149,657,261 and stores by 46,858,058, while native code grows by 22,904 bytes. Those counts describe emitted instructions, not hardware memory traffic.

The measured source is integrated as an experimental runtime improvement. Large Nu identical-tool controls showed substantial variation; none is subtracted from these results. These are selected original tests, not whole-application support. The initial two-workflow report is preserved alongside this update.
