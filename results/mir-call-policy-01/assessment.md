# Ordinary MIR inlining loses with the current native-call JIT

Both predeclared gates fail. The current enlarged inlining policy remains selected; no runtime or exporter implementation changed.

| Workflow | Native | Enlarged | Ordinary | Ordinary paired wall | Ordinary paired CPU |
| --- | ---: | ---: | ---: | ---: | ---: |
| folded-literal-trie | 1.685s | 2.008s | 2.111s | +4.55% | +5.56% |
| token-phrase | 2.004s | 4.334s | 4.635s | +6.88% | +7.04% |

All 168 commands, 30 edited pairs and 84 artifacts verify, including original assertions, wrong-edit rejection, source restoration and separate Cargo-check controls. All 72 successful VM runs report zero declined functions. Baseline/candidate in the historical harness mean ordinary/enlarged here.

Ordinary inlining produces smaller artifacts and less generated native code, but executes more guest instructions and Calls. Folded median execution rises from 1.061s to 1.191s; token from 2.978s to 3.339s. Token Cargo time falls from 1.277s to 1.213s, insufficient to offset execution. These are recorded stages, not an isolated causal attribution.

Keep all failures. No threshold sweep or timing rerun is planned. The native gap remains; aggregate storage and full-suite compatibility still need work.
