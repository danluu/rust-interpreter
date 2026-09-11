# Control-flow experiment: initial edited-command comparison

Jump threading and deterministic block layout preserve all 143 bytecode tests, 47,004 native differential commands and 245 TLS checks. The pass keeps function IDs, layouts, register initialization, switch precedence, call order and cycles. Layout falls back to threading when code would grow.

Each workflow uses five real production edits, original unchanged assertions, independent tool caches and a rejected wrong edit. Both modes use MIR3 and the same eightfold MIR inlining budget. All 14 artifact pairs change; all parent artifacts exactly match the preceding run. The original folded artifact exactly matches the isolated layout probe.

| Workflow | Command wins | Paired command change | Execution wins | Paired execution change | CFG export cost | Native wins |
|---|---:|---:|---:|---:|---:|---:|
| folded-literal-trie | 3/5 | -24.227 ms | 4/5 | -8.939 ms | 13.534 ms | 0/5 |
| forward-anchored-tls | 4/5 | -12.223 ms | 5/5 | -4.179 ms | 6.040 ms | 5/5 |

The candidate wins 7/10 complete commands and 9/10 execution stages. Cargo variation contributes materially to the command differences. Independent medians and medians of paired differences can disagree: TLS has a higher candidate median despite four paired wins. Native still wins every folded-trie comparison. Both actual VM binaries changed, while VM/emitter source stayed fixed.

The isolated same-VM probe saved a paired 19 ms in folded execution. The integrated pass spends roughly 13 ms during export, so next compare an implementation that clones each retained instruction only once. Preserve exact artifact and pass-report equality before measuring complete commands again. No broad warm-build gain or fresh all-body coverage is claimed for this candidate.
