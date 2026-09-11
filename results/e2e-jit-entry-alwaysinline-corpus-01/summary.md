# JIT entry wrapper: production-edit qualification

The host wrapper for entering generated code remained out of line in a CPU profile despite a normal inline hint. Forcing it to inline reduces that repeated transition cost. The guest emitter and bytecode format are unchanged.

All seven established workflows and an eighth word64 configuration passed after five cumulative production refactors. Original test source stayed unchanged; every mode rejected the deliberately wrong edit; all five source pins were restored. One frozen tool build was used throughout.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-jit-entry-alwaysinline-01/summary.md) | 1.601 s | 16.742 s | 3.087 s |
| [pgrust](../e2e-workflow-pgrust-jit-entry-alwaysinline-01/summary.md) | 0.662 s | 0.765 s | 0.536 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-jit-entry-alwaysinline-01/summary.md) | 1.345 s | 0.718 s | 0.700 s |
| [nushell](../e2e-workflow-nushell-jit-entry-alwaysinline-01/summary.md) | 0.622 s | 0.432 s | 0.435 s |
| [ruff](../e2e-workflow-ruff-jit-entry-alwaysinline-01/summary.md) | 5.461 s | 2.998 s | 2.824 s |
| [rg-aot](../e2e-workflow-rg-aot-jit-entry-alwaysinline-01/summary.md) | 0.550 s | 0.194 s | 0.190 s |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-jit-entry-alwaysinline-01/summary.md) | 12.962 s | 6.777 s | 6.002 s |
| [fre-word64-inline8](../e2e-workflow-fre-word64-inline8-jit-entry-alwaysinline-01/summary.md) | 1.687 s | 14.059 s | 2.431 s |

Complete-command medians include Cargo, strict frontend checking, export, launch, and test execution after real source edits. The second word64 row explicitly multiplies MIR inlining thresholds by eight; other workflow flags retain their preceding settings. These are focused existing tests in larger workspaces, not full applications or suites.

Five alternating same-bytecode runtime pairs measured 2.458 versus 2.274 s at default MIR thresholds (four candidate wins), and 1.700 versus 1.579 s at eightfold thresholds (five wins). All pairs preserve instruction count, peak guest memory, and generated code size. The expanded native differential/rejection suite passed 21,927 commands, including all three inlining experiments; all 93 launcher checks and 52 bytecode tests also pass. The bytecode tests include many boundary/alias cases within each reported test.

Full command timings also include Cargo and shared-host variation. The JSON retains cold commands and per-stage medians; stage medians need not sum to command medians. Metadata-sysroot commands exclude the separately recorded 10.997 s reusable setup.

[Validation and raw paired evidence](../jit-entry-alwaysinline-validation-01.json), [MIR configuration comparison](../mir-inlining-word64-01/summary.md).
