# Opt-in leaf inlining: complete production-edit comparison

The candidate wins 13 of 15 complete-command pairs against the retained JIT baseline. The option remains experimental while broader project and test coverage is checked. It is disabled by default.

Each workflow applies five cumulative production-code refactors without changing the original tests. Native, baseline JIT and candidate JIT use separate Cargo caches and alternate order. Every mode rejects a deliberately wrong production edit. Full subprocess time includes Cargo, strict frontend checking, lowering, inlining, bytecode loading, JIT construction and test execution.

| Workflow | Native median (s) | Baseline JIT median (s) | Inlining candidate median (s) | Median paired change (ms) | Candidate wins |
|---|---:|---:|---:|---:|---:|
| [fre-word64](../e2e-paired-fre-word64-leaf-inline-01/summary.md) | 1.638328 | 2.568255 | 2.444749 | -123.506 | 5/5 |
| [fre-word64-inline8](../e2e-paired-fre-word64-inline8-leaf-inline-01/summary.md) | 1.734255 | 1.936057 | 1.942863 | -32.774 | 3/5 |
| [pgrust-sha1-inline8](../e2e-paired-pgrust-sha1-inline8-leaf-inline-01/summary.md) | 0.780218 | 0.985454 | 0.971142 | -13.593 | 5/5 |

The transformation takes 0.8–2.2 ms per export. Candidate execution is faster in every pair; its median paired execution changes are −110 ms, −69 ms and −17 ms, respectively. The two inline8 complete-command losses coincide with higher Cargo time, including a retained +362 ms Cargo-stage difference. No sample is excluded. A stage association does not identify the cause of shared-host variation.

Native is still faster on all three compute workflows. Five samples per workflow are not confidence intervals or whole-suite results. Cold commands use empty per-mode artifact caches, but exclude downloads, tool bootstrap and shared standard-library MIR installation. The baseline and candidate VM binary hashes differ after rebuilding the shared bytecode library; these compare complete tool builds. The prior runtime screen separately compared transformed and original artifacts using exactly the same VM.

Correctness gates pass: 84 bytecode tests, 24 option/cache/source-edit checks, 71 SIMD checks, 79 audit checks, 99 existing launcher checks, and 23,502 native differential/rejection commands each with the option disabled and enabled. Of 161 successful option-enabled exports in the latter suite, 121 actually inline calls. The integrated transformation exactly matches the V2 prototype artifacts on all three retained workloads.

[Integration validation](../leaf-inline-integrated-validation-01.json), [option-enabled differential suite](../leaf-inline-native-validation-01.json), [artifact equivalence](../leaf-inline-integrated-artifacts-01.json), [same-VM runtime screen](../leaf-inline-runtime-02/summary.md).
