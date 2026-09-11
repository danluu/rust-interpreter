# Scalar constants: seven production-edit workflows

All seven workflows passed after five cumulative production refactors. Original test source was unchanged, the deliberately wrong edit failed in all three modes, and all five source pins were restored. One frozen tool build was used throughout.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-scalar-constant-01/summary.md) | 1.698 s | 16.953 s | 3.472 s |
| [pgrust](../e2e-workflow-pgrust-scalar-constant-01/summary.md) | 0.658 s | 0.764 s | 0.542 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-scalar-constant-01/summary.md) | 1.363 s | 0.753 s | 0.774 s |
| [nushell](../e2e-workflow-nushell-scalar-constant-01/summary.md) | 0.632 s | 0.428 s | 0.420 s |
| [ruff](../e2e-workflow-ruff-scalar-constant-01/summary.md) | 5.645 s | 2.883 s | 2.780 s |
| [rg-aot](../e2e-workflow-rg-aot-scalar-constant-01/summary.md) | 0.569 s | 0.199 s | 0.193 s |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-scalar-constant-01/summary.md) | 11.330 s | 6.312 s | 5.255 s |

Medians include Cargo, strict frontend checking, export, launcher, and test execution after real source edits. These are focused workflows within large workspaces, not full applications or complete test suites. Guest runtime uses the custom interpreter or direct AArch64 emitter.

Scalar constants now enter value consumers directly, while calls and other address consumers retain storage. Wrapped constant-pointer relocations also preserve the 64-bit target width. The change passed 11,190 native differential/rejection commands and 93 launcher checks. Five alternating runs of bytecode exported from identical production source used the same VM binary and measured 2.596 versus 2.547 s JIT runtime, with five candidate wins. The complete word64 command median remained approximately flat (3.441 versus 3.472 s), while interpretation improved from 17.864 to 16.953 s. Compilation and host variability remain part of the end-to-end comparison; the paired run isolates the exported-artifact change.

The JSON records cold command times and per-stage medians. Cold commands using the metadata sysroot exclude the separately recorded 10.997 s reusable MIR setup. Stage medians need not sum to total-command medians.

[Constant validation and paired evidence](../scalar-constant-validation-01.json).

A subsequent three-pair interpreter comparison, on the same archived source/artifacts and VM binary, measured 16.712 versus 16.196 s and won three of three pairs. It confirms a runtime improvement separately from Cargo and frontend variation; the raw records are linked in the validation JSON.
