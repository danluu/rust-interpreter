# Control-flow simplification with one instruction copy

Eight-workflow cohort complete.

The exporter threads jumps, removes unreachable code and lays out basic blocks after call optimization.
It keeps function IDs, frames, register initialization, switch precedence, call order and cycles. Layout falls back to threading if code grows.
An intermediate instruction-stream clone is removed: all 14 artifacts and pass reports exactly match the first CFG prototype.

All 143 bytecode tests, 47,004 native differential commands, compiler/launcher checks and 245 TLS checks pass.
VM/emitter source is unchanged. Actual tool binaries differ from the parent; the VM instruction section matches the first CFG prototype.

The isolated same-VM CFG screen wins 5/6 pairs (-19 ms paired). The separate cost refactor wins all 84 comparisons, saving about 1.7 ms for folded trie and 0.8 ms for TLS.
Those screens are separate from the production-edit measurements below.

Every workflow uses five real production edits, original unchanged assertions and a wrong edit rejected by both builds. Baseline and candidate use identical MIR settings.
Changes are medians of paired candidate-minus-parent differences; negative values are faster.

| Workflow | Native / parent / candidate medians (s) | Command change (ms) | Execution change (ms) | Wins vs parent / native |
|---|---:|---:|---:|---:|
| [folded-literal-trie](../paired-cfg-folded-literal-trie-02/summary.md) | 1.703 / 2.904 / 2.900 | -24.3 | -17.7 | 3/5 / 0/5 |
| [forward-anchored-tls](../paired-cfg-forward-anchored-tls-02/summary.md) | 1.714 / 1.255 / 1.317 | -7.7 | -4.3 | 3/5 / 5/5 |
| [pgrust](../paired-cfg-corpus-pgrust-01/summary.md) | 0.632 / 0.506 / 0.504 | +0.2 | -0.6 | 2/5 / 5/5 |
| [ruff](../paired-cfg-corpus-ruff-01/summary.md) | 5.780 / 3.153 / 3.331 | -3.4 | +0.1 | 3/5 / 5/5 |
| [nushell](../paired-cfg-corpus-nushell-01/summary.md) | 0.644 / 0.431 / 0.438 | +2.5 | +0.2 | 2/5 / 5/5 |
| [rg-aot](../paired-cfg-corpus-rg-aot-01/summary.md) | 0.540 / 0.196 / 0.196 | +0.6 | +0.3 | 2/5 / 5/5 |
| [pgrust-sha1-inline8](../paired-cfg-corpus-pgrust-sha1-inline8-01/summary.md) | 0.763 / 0.915 / 0.908 | +0.9 | +0.0 | 2/5 / 0/5 |
| [nushell-type-relations](../paired-cfg-corpus-nushell-type-relations-01/summary.md) | 19.571 / 9.473 / 7.116 | -1353.8 | +0.1 | 3/5 / 5/5 |

The candidate wins 20/40 complete commands and 21/40 execution stages. It wins 30/40 against native.
Cargo variation materially affects command timings. Independent medians need not agree with medians of paired differences; all raw samples are retained.

Fresh export and execution of all 389 fre bodies yields 381 passes, one exact previous allocation-capacity error, and seven ignored tests. All 382 fresh native controls pass.
Maximum generated native code is 9,937,476 bytes; every passing guest test has zero declined functions.

All 56 artifact pairs were audited; 0 pairs are identical. Every baseline artifact exactly matches the preceding retained 57f3 run.
All fourteen folded/TLS candidate artifacts also match the initial CFG build; the original folded artifact matches the isolated layout probe.
Native controls use standard Cargo settings; they do not establish the best available native development configuration.
These are selected library-test workflows. Whole applications, arbitrary OS/FFI calls, guest threads and native unwinding remain unsupported.
A broad warm-build improvement is not established.

Retain the pass as an experimental runtime improvement. Folded trie saves a paired 24 ms per edited command (18 ms in execution), and TLS saves 8 ms (4 ms in execution). The full cohort wins only 20/40 against its parent; short workflows are effectively flat. Larger Nushell saves 1.354 s paired in warm commands, chiefly in Cargo, but its cold candidate takes 106.371 s versus 72.001 s for the parent. These measurements do not establish a broad warm-build improvement or a causal explanation for the cold regression. Native still wins all 10 folded-trie/SHA-1 comparisons. Next inspect MIR frame lifetimes and initialization volume before another runtime change.
