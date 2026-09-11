# Single-thread TLS and control-flow reachability corpus

Five cumulative production edits per workflow, existing tests unchanged, deliberate wrong edit rejected by all modes. Selected tests, not full applications.

Strict frontend checking; own bytecode interpreter and AArch64 JIT. Bytecode v5.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-tls-01/summary.md) | 1.703s | 17.677s | 3.735s |
| [pgrust](../e2e-workflow-pgrust-tls-01/summary.md) | 0.647s | 0.831s | 0.559s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-tls-01/summary.md) | 1.423s | 0.773s | 0.757s |
| [nushell](../e2e-workflow-nushell-tls-01/summary.md) | 0.629s | 0.436s | 0.440s |
| [ruff](../e2e-workflow-ruff-tls-01/summary.md) | 5.948s | 3.221s | 3.363s |
| [rg-aot](../e2e-workflow-rg-aot-tls-01/summary.md) | 0.546s | 0.197s | 0.193s |

The separate [fourteen-test Nushell type workflow](../e2e-workflow-nushell-type-relations-01/summary.md) passed on this same tool build (9.600/5.120/5.303 s native/interpreter/JIT).

All five source pins were restored and checked, apart from ownership/metadata markers. Five samples on a shared host are not a confidence interval. Small differences across runs are not isolated runtime effects; see stage medians in summary.json. Word64 remains faster natively.

The additional MIR setup costs 10.997 s and is excluded from the commands that use it. Guest threads, TLS destructor registration, general OS/FFI, and native unwinding remain unsupported.
