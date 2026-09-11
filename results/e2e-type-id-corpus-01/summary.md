# TypeId lowering: production-edit qualification

The exporter now retains the numeric TypeId hash fragments supplied by the compiler. The VM binary and bytecode format are unchanged. All nine production workflows pass on one frozen build: five cumulative production refactors, unchanged original test source, wrong-edit rejection in every mode, and all five source pins restored.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-type-id-01/summary.md) | 1.651 s | 16.688 s | 3.075 s |
| [pgrust](../e2e-workflow-pgrust-type-id-01/summary.md) | 0.640 s | 0.772 s | 0.550 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-type-id-01/summary.md) | 1.373 s | 0.753 s | 0.758 s |
| [nushell](../e2e-workflow-nushell-type-id-01/summary.md) | 0.636 s | 0.450 s | 0.441 s |
| [ruff](../e2e-workflow-ruff-type-id-01/summary.md) | 6.108 s | 3.309 s | 3.398 s |
| [rg-aot](../e2e-workflow-rg-aot-type-id-01/summary.md) | 0.528 s | 0.191 s | 0.190 s |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-type-id-01/summary.md) | 12.086 s | 7.443 s | 7.102 s |
| [fre-word64-inline8](../e2e-workflow-fre-word64-inline8-type-id-01/summary.md) | 2.092 s | 14.246 s | 2.612 s |
| [pgrust-sha1-inline8](../e2e-workflow-pgrust-sha1-inline8-type-id-01/summary.md) | 0.808 s | 5.687 s | 1.234 s |

These complete edit-to-test command medians include Cargo, strict checking, export, launch, and execution. They are focused existing tests in larger workspaces, not full applications or test suites. The explicit eightfold MIR configurations retain development checks. Cold commands and stage medians are in the JSON; metadata-sysroot commands exclude the separately recorded 10.997 s reusable setup. Historical timing differences are not isolated effects of this compatibility change.

All 23,277 native differential/rejection commands and 93 launcher checks pass. TypeId and Any also execute with the installed sysroot; the error-downcast fixture needs metadata MIR. The complete Nushell audit remains 162/279 lowerable bodies: seven former TypeId blockers now reach missing OS or TLS support. No new Nushell test execution success is claimed.

[Validation and raw evidence](../type-id-validation-01.json), [full lowering audit](../lowering-audit-nushell-09/summary.md).
