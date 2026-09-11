# Closure-pointer and zero-sized call ABI corpus

Five real cumulative production edits per workflow, native test oracle, deliberate failing edit, source restoration. Selected tests only, not full applications.

Strict frontend validation; own interpreter and AArch64 JIT. No deferred checking. Tool key `f06fe818e199961a2f08c2603690ae4f154605690023f7f4d710ba0b701b4dbd`.

| Workflow | Native | Interpreter | JIT |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-call-abi-01/summary.md) | 1.707s | 17.378s | 3.793s |
| [pgrust](../e2e-workflow-pgrust-call-abi-01/summary.md) | 0.653s | 0.817s | 0.551s |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-call-abi-01/summary.md) | 1.408s | 0.740s | 0.762s |
| [nushell](../e2e-workflow-nushell-call-abi-01/summary.md) | 0.688s | 0.424s | 0.420s |
| [ruff](../e2e-workflow-ruff-call-abi-01/summary.md) | 5.714s | 2.822s | 2.748s |
| [rg-aot](../e2e-workflow-rg-aot-call-abi-01/summary.md) | 0.538s | 0.196s | 0.194s |

These are medians of edit/build/test loops, not unchanged builds. The runtime executable is unchanged from the preceding corpus. Timing changes here are not evidence of a runtime speedup.

All five source pins were verified clean apart from ownership/metadata markers. The full fourteen-test Nushell type family remains blocked at thread-local storage before guest execution; it is not included here.
