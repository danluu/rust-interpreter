# Linked compiled blocks: production-edit qualification

The custom AArch64 emitter links compiled successors within a guest function. Every block consumes a checked virtual-instruction budget; partial tails and unsupported instructions return to the VM. Native profiling counts every linked block. Both binary hashes and exact source inputs are recorded.

All nine workflows pass on one frozen build, with five real production refactors, unchanged original tests, wrong-edit rejection in all modes, and restored source pins.

| Workflow | Native (s) | Interpreter (s) | JIT (s) |
|---|---:|---:|---:|
| [fre-word64](../e2e-workflow-fre-word64-jit-region-linking-01/summary.md) | 2.049 | 15.316 | 2.485 |
| [pgrust](../e2e-workflow-pgrust-jit-region-linking-01/summary.md) | 0.688 | 0.759 | 0.534 |
| [fre-class-sequence](../e2e-workflow-fre-class-sequence-jit-region-linking-01/summary.md) | 1.397 | 0.723 | 0.714 |
| [nushell](../e2e-workflow-nushell-jit-region-linking-01/summary.md) | 0.626 | 0.435 | 0.437 |
| [ruff](../e2e-workflow-ruff-jit-region-linking-01/summary.md) | 5.540 | 2.923 | 2.842 |
| [rg-aot](../e2e-workflow-rg-aot-jit-region-linking-01/summary.md) | 0.520 | 0.198 | 0.195 |
| [nushell-type-relations](../e2e-workflow-nushell-type-relations-jit-region-linking-01/summary.md) | 10.151 | 6.018 | 5.759 |
| [fre-word64-inline8](../e2e-workflow-fre-word64-inline8-jit-region-linking-01/summary.md) | 1.753 | 13.006 | 1.893 |
| [pgrust-sha1-inline8](../e2e-workflow-pgrust-sha1-inline8-jit-region-linking-01/summary.md) | 0.762 | 5.333 | 1.008 |

Times cover the complete Cargo/build/test subprocess. Cold times and Cargo/execution stages are in JSON. Metadata-sysroot setup, downloads, and compiler-tool bootstrap are excluded. Native is a separately compiled control. No native guest fallback is used.

The Nushell type-relations cold custom commands varied from 164.600 s interpreted to 63.531 s JIT; their Cargo stages were 164.475 s and 63.339 s. The VM subprocesses took 0.020 s and 0.098 s, including startup and engine setup. This single-run cold spread is retained, not treated as a stable engine ranking. The controlled paired comparisons provide the evidence for the runtime change.

| Identical-bytecode runtime | Before (s) | After (s) | Candidate wins |
|---|---:|---:|---:|
| jit:word64-default | 2.195 | 1.725 | 6/6 |
| jit:word64-inline8 | 1.472 | 1.093 | 6/6 |
| jit:sha1-inline8 | 0.646 | 0.460 | 6/6 |
| interpreter:word64-default | 14.542 | 14.493 | 4/6 |
| interpreter:sha1-inline8 | 4.726 | 4.729 | 2/6 |

All 60 runtime commands pass. The build also passes 73 bytecode tests, 23,502 native differential/rejection commands, and 99 launcher checks. Tests verify linked loops, region boundaries, large register addresses, full-u128 switches, short interpreter gaps, heap-copy scratch registers, exact budget/fault precedence, profile accounting, branch relocations, and native x19/SP preservation on every exit kind.

[Validation](../jit-region-linking-validation-01.json). [Paired complete-command comparison](../paired-region-linking-e2e-01/summary.md).
