# Checked division: seven production-edit workflows

All seven workflows passed after five cumulative production refactors. Original test source was unchanged, the deliberately wrong edit failed in all three modes, and all five source pins were restored. One frozen tool build was used throughout.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-jit-division-01/summary.md) | 1.770 s | 16.790 s | 3.330 s |
| [pgrust](../e2e-workflow-pgrust-jit-division-01/summary.md) | 0.633 s | 0.772 s | 0.540 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-jit-division-01/summary.md) | 1.421 s | 0.777 s | 0.811 s |
| [nushell](../e2e-workflow-nushell-jit-division-01/summary.md) | 0.668 s | 0.430 s | 0.427 s |
| [ruff](../e2e-workflow-ruff-jit-division-01/summary.md) | 5.994 s | 3.106 s | 2.977 s |
| [rg-aot](../e2e-workflow-rg-aot-jit-division-01/summary.md) | 0.545 s | 0.192 s | 0.195 s |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-jit-division-01/summary.md) | 11.074 s | 5.095 s | 5.246 s |

Medians include Cargo, strict frontend checking, export, launcher, and test execution after real source edits. These are focused workflows within large workspaces, not full applications or complete test suites. Guest runtime uses the custom interpreter or direct AArch64 emitter.

Checked division and remainder through 64 bits now execute in the custom emitter, preserving zero-divisor and signed MIN/-1 errors. Native differential/rejection checks (11,865 commands), 93 launcher checks, and boundary/alias/budget/fault-ordering tests passed. Five alternating pairs on identical bytecode reduced JIT runtime from 2.571 to 2.481 s, winning all five pairs with unchanged instruction count and peak guest memory. Generated code remained approximately unchanged in size. The word64 complete-command median fell from the preceding scalar corpus's 3.472 to 3.330 s; native remains faster at 1.770 s in this run. Other historical corpus differences include Cargo and host variability and are not isolated runtime effects.

The JSON records cold command times and per-stage medians. Cold commands using the metadata sysroot exclude the separately recorded 10.997 s reusable MIR setup. Stage medians need not sum to total-command medians.

[Division validation and paired evidence](../jit-division-validation-01.json).
