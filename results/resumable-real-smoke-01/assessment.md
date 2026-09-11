# Original-artifact execution with resumable native Calls

Git `e1bec3e` (runtime `5574d10`), tool `035ef708`, passes the original folded-trie and token artifacts with `--jit-resumable-calls --jit-persistent-registers`. The original b2 baseline also passes both. All commands return zero and print zero; original assertions and fixed limits are preserved. All frozen inputs were hash-verified.

| Artifact | Mode | Logical instructions | Native entries | Resumable Calls | Resumable Returns | JIT bytes |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| folded-literal-trie | baseline | 4138403285 | 43732357 | 0 | 0 | 3533256 |
| folded-literal-trie | candidate | 4138403285 | 85769 | 25913904 | 25916861 | 5824108 |
| token-phrase | baseline | 13369586800 | 244306062 | 0 | 0 | 8674972 |
| token-phrase | candidate | 13369612535 | 22417728 | 110504850 | 111381987 | 14608884 |

No functions declined at the code budget. Token invokes guest randomness, so independently executed logical instruction counts differ. Returns can exceed native Calls because native code also returns from frames pushed by the VM.

This run uses saved artifacts: it is a correctness/coverage smoke check, not an end-to-end source-edit performance comparison. Toolchain, compilation/export and artifact creation are excluded. The original three-cycle b2 gates and held-out/broader qualification remain required.

[Raw command and hash evidence](summary.json) · [Optimized tests](../resumable-release-01/summary.json) · [CLI and receipt checks](../resumable-cli-01/summary.json)
