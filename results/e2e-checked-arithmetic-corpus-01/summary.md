# Checked arithmetic: seven production-edit workflows

All seven workflows passed after five cumulative production refactors. Original test source was unchanged, the deliberately wrong edit failed in all three modes, and all five source pins were restored. One frozen tool build was used throughout.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-checked-arithmetic-01/summary.md) | 1.734 s | 17.864 s | 3.441 s |
| [pgrust](../e2e-workflow-pgrust-checked-arithmetic-01/summary.md) | 0.661 s | 0.816 s | 0.546 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-checked-arithmetic-01/summary.md) | 1.398 s | 0.752 s | 0.743 s |
| [nushell](../e2e-workflow-nushell-checked-arithmetic-01/summary.md) | 0.630 s | 0.447 s | 0.435 s |
| [ruff](../e2e-workflow-ruff-checked-arithmetic-01/summary.md) | 5.601 s | 3.113 s | 2.867 s |
| [rg-aot](../e2e-workflow-rg-aot-checked-arithmetic-01/summary.md) | 0.570 s | 0.196 s | 0.189 s |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-checked-arithmetic-01/summary.md) | 11.233 s | 6.362 s | 6.318 s |

Medians include Cargo, strict frontend checking, export, launcher, and test execution after real source edits. These are focused workflows within large workspaces, not full applications or complete test suites. Guest runtime uses the custom interpreter or direct AArch64 emitter.

The checked add/subtract/multiply emitter reduced paired word64 runtime from 2.897 to 2.609 s, winning all five alternating pairs on identical bytecode and output. Its complete edited-command median fell from the preceding TLS corpus's 3.735 to 3.441 s; native remains faster at 1.734 s in this run. Other historical differences include Cargo and host variability and are not isolated runtime effects.

The JSON records cold command times and per-stage medians. Cold commands using the metadata sysroot exclude the separately recorded 10.997 s reusable MIR setup. Stage medians need not sum to total-command medians.

[Arithmetic validation and paired evidence](../checked-arithmetic-validation-01.json).
