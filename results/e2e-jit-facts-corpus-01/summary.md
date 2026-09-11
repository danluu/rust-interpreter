# Production-edit regressions after runtime optimization

All six workflows across five projects passed five cumulative production-body
refactors with their existing tests unchanged. Every mode also rejected the
wrong production edit. Tools and benchmark scripts were frozen throughout the
serial run, and every owned source snapshot was restored to its pinned revision.
Private source and detailed records remain under `.work`.

Times include Cargo, launcher, compilation, and execution. These are focused
workflows, not complete suites or applications. Five samples on a shared host
are not confidence intervals.

| Existing-test workflow | Native | Interpreter | Custom JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-jit-facts-01/summary.md) | 1.644 s | 17.638 s | 4.660 s |
| [pgrust](../e2e-workflow-pgrust-jit-facts-01/summary.md) | 0.654 s | 0.848 s | 0.576 s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-jit-facts-01/summary.md) | 1.310 s | 0.736 s | 0.737 s |
| [nushell](../e2e-workflow-nushell-jit-facts-01/summary.md) | 0.620 s | 0.440 s | 0.432 s |
| [ruff](../e2e-workflow-ruff-jit-facts-01/summary.md) | 5.428 s | 2.996 s | 2.816 s |
| [rg-aot](../e2e-workflow-rg-aot-jit-facts-01/summary.md) | 0.553 s | 0.190 s | 0.192 s |

Word64 explicitly enables MIR optimization level 3 for the custom engines;
overflow checks and ordinary frontend checking remain enabled. Other rows
preserve their existing Cargo profiles. The word64, Nushell, and Ruff workflows
use reusable standard-library MIR; its approximately 11 s original setup is
excluded. Native uses the installed standard library.

The larger word64 group remains slower than native, despite improving from
13.164 s to 4.660 s with the JIT. Its original exhaustive inputs stay in the
benchmark. The short workflows retain useful whole-command savings. These
results support keeping the runtime changes while targeting the remaining
call/branch and frame-management costs with a separate CPU profile.

Cold rows below start with separate empty workspace artifact caches. Tool
bootstrap, downloads, installed sysroot, and OS file-cache coldness are excluded.

| Workflow | Native cold | Interpreter cold | JIT cold |
|---|---:|---:|---:|
| fre-word64 | 7.119 s | 21.921 s | 9.161 s |
| pgrust | 1.063 s | 0.841 s | 0.587 s |
| fre-class-sequence | 6.458 s | 4.403 s | 4.168 s |
| nushell | 22.103 s | 20.537 s | 20.924 s |
| ruff | 57.496 s | 28.142 s | 28.291 s |
| rg-aot | 3.615 s | 2.705 s | 2.834 s |

Tool key: `10fc316e97cb8b5e0bbfa6d3f7f282c09c46d3dfbc0e18f6c4fd83c5f09c37f4`. Source revisions and script/binary hashes are retained in summary.json.
