# Extended SIMD coverage: production-edit qualification

All eleven workflows pass on one frozen build, with five real production edits, unchanged original tests, rejected wrong edits, and all five source pins restored. The interpreter and direct AArch64 JIT execute their own bytecode; native Rust is the separate control.

| Workflow | Native (s) | Interpreter (s) | JIT (s) |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-simd-coverage-01/summary.md) | 1.657 | 15.201 | 2.538 |
| [pgrust](../e2e-workflow-pgrust-simd-coverage-01/summary.md) | 0.663 | 0.766 | 0.539 |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-simd-coverage-01/summary.md) | 1.360 | 0.774 | 0.762 |
| [nushell](../e2e-workflow-nushell-simd-coverage-01/summary.md) | 0.655 | 0.461 | 0.459 |
| [ruff](../e2e-workflow-ruff-simd-coverage-01/summary.md) | 5.608 | 3.200 | 2.960 |
| [rg-aot](../e2e-workflow-rg-aot-simd-coverage-01/summary.md) | 0.557 | 0.194 | 0.194 |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-simd-coverage-01/summary.md) | 15.738 | 8.836 | 8.662 |
| [fre-word64-inline8](../e2e-workflow-fre-word64-inline8-simd-coverage-01/summary.md) | 3.404 | 14.141 | 2.801 |
| [pgrust-sha1-inline8](../e2e-workflow-pgrust-sha1-inline8-simd-coverage-02/summary.md) | 0.783 | 5.279 | 1.006 |
| [fre-grapheme-scalar-dfa](../e2e-workflow-fre-grapheme-scalar-dfa-simd-coverage-01/summary.md) | 1.951 | 1.234 | 1.164 |
| [fre-packed-literal-set](../e2e-workflow-fre-packed-literal-set-simd-coverage-01/summary.md) | 2.212 | 1.286 | 1.205 |

Times include Cargo, compilation, launch and execution after each edit. Cold commands and stage breakdowns are retained in JSON. Setup is excluded and recorded by each workflow. These focused workloads do not demonstrate complete application or suite support. Separate historical medians are not isolated causal comparisons.

The first SHA-1 timing run was excluded because owned cache deletion overlapped its first positive edit. The complete workflow was rerun with fresh caches after cleanup finished; the table uses that isolated rerun. Both runs and the contemporaneous exclusion decision are preserved.

The new lowering implements byte table lookup and ordered integer SIMD reductions using existing scalar instructions. The VM binary is unchanged. It passes 71 focused SIMD commands, 79 audit-artifact commands, 99 launcher checks, and 23,502 native differential/rejection commands. Retained execution evidence covers 231 ordinary fre bodies; 158 remain lowering-blocked.

[Capability evidence](../simd-ordered-capability-01/summary.md), [validation](../simd-ordered-validation-01.json), [raw timing and provenance](summary.json).
