# Leaf inlining across eleven production-edit workflows

Retain the bounded leaf inliner as an explicit option, disabled by default. All eleven workflows pass their original tests and reject deliberately wrong production edits. The candidate wins 35/55 complete-command pairs. The clearest execution benefits are in the word64 and SHA-1 compute workloads; short and frontend-heavy workflows are mixed.

| Workflow | Native median (s) | Baseline JIT median (s) | Candidate JIT median (s) | Median paired change (ms) | Wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-leaf-inline-01/summary.md) | 1.638328 | 2.568255 | 2.444749 | -123.506 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-leaf-inline-01/summary.md) | 1.734255 | 1.936057 | 1.942863 | -32.774 | 3/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-leaf-inline-01/summary.md) | 0.780218 | 0.985454 | 0.971142 | -13.593 | 5/5 |
| [pgrust](../e2e-paired-pgrust-leaf-inline-broad-01/summary.md) | 0.659562 | 0.538571 | 0.538278 | -9.477 | 3/5 |
| [fre-class-sequence](../e2e-paired-fre-class-sequence-leaf-inline-broad-01/summary.md) | 1.393825 | 0.746961 | 0.768358 | +21.916 | 2/5 |
| [nushell](../e2e-paired-nushell-leaf-inline-broad-01/summary.md) | 0.646057 | 0.443271 | 0.434157 | -5.122 | 4/5 |
| [ruff](../e2e-paired-ruff-leaf-inline-broad-01/summary.md) | 5.800282 | 2.942753 | 2.789302 | -136.969 | 3/5 |
| [rg-aot](../e2e-paired-rg-aot-leaf-inline-broad-01/summary.md) | 0.546630 | 0.200164 | 0.202884 | +2.720 | 2/5 |
| [nushell-type-relations](../e2e-paired-nushell-type-relations-leaf-inline-broad-01/summary.md) | 8.553151 | 5.037088 | 5.261549 | +306.833 | 1/5 |
| [fre-grapheme-scalar-dfa](../e2e-paired-fre-grapheme-scalar-dfa-leaf-inline-broad-01/summary.md) | 1.553197 | 1.051973 | 1.037186 | -16.500 | 4/5 |
| [fre-packed-literal-set](../e2e-paired-fre-packed-literal-set-leaf-inline-broad-01/summary.md) | 2.064080 | 1.179452 | 1.150505 | -20.445 | 3/5 |

Each workflow contains five cumulative production-body refactors. Tests remain unchanged; modes alternate order and use separate artifact caches. Timers include the full Cargo/check/lower/inline/load/JIT/test command. Native uses the same selected tests. Every executed bytecode artifact and all timing samples are retained. These compare complete immutable tool builds; their VM hashes differ. The earlier runtime screen isolated artifact changes using one identical VM.

The word64 execution stage improves in all ten pairs across its two configurations; SHA-1 improves in all five. Inlining itself costs milliseconds. The Nushell type-relations candidate loses four pairs, with a +307 ms median complete-command change: its median Cargo-stage change is +292 ms, versus about +1 ms in execution and 1.7 ms for the transformation. This observation does not establish the cause of Cargo variability. Apparent full-command improvements in the short workflows likewise do not establish a runtime benefit.

Existing VM instrumentation measures candidate JIT construction at about 0.7–11 ms across these workflows. That is a small part of the full edited-command times. A persistent JIT-code cache would therefore address little of the currently measured delay. The next runtime experiment targets repeated VM transitions for the local frame fills inserted by the inliner.

The transformed fre audit classifies all 389 original bodies: all 231 supported ordinary tests agree with fresh native executions, and 158 remain lowering-blocked. This is fresh execution evidence for every supported body, using an explicit 100-billion-instruction ceiling; it is not complete-suite support or a speedup measurement. Existing unsupported threading, OS interfaces and unwind behavior remain limitations.

Other checks pass: 84 bytecode tests, 24 option/cache/source-edit checks, 71 SIMD checks, 79 audit checks, 99 launcher checks, and 23,502 native differential/rejection commands with the option disabled plus another 23,502 with it enabled. Cargo tracks the option; old exporters reject it; all five source pins are restored.

Five samples per workflow on a shared host are not confidence intervals. Native remains faster for the compute workflows. Cold commands start with empty per-mode artifact caches but exclude downloads, tool bootstrap, OS cache coldness and shared standard-library MIR installation. Cleanup completed at explicit boundaries before measurements resumed; native controls, tools, source pins, reports and bytecode were retained.

[Compute comparison](../paired-leaf-inline-e2e-01/summary.md), [fresh fre execution survey](../audit-execution-fre-leaf-inline-01/summary.md), [integration checks](../leaf-inline-integrated-validation-01.json), [option-enabled differential checks](../leaf-inline-native-validation-01.json).
