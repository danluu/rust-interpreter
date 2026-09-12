# Keep interpreter frame state across instructions

The candidate passes the fixed public runtime screen and five additional workload checks. It holds the current function and checked register slice across ordinary interpreter instructions and branches, returning to the outer loop for calls, returns, TLS transitions and each JIT fallback. It uses one opcode dispatcher, ordinary safe borrows and the existing bounds checks.

The baseline is the previously qualified arithmetic/scalar-memory VM from a1f8922, incorporated into parent 04999a2 without Rust source changes. These improvements are relative to that VM.

| Workload | Interpreter wall change | Interpreter CPU change | JIT wall change |
|---|---:|---:|---:|
| pgrust | -26.79% | -26.94% | -1.06% |
| nushell | -3.12% | -6.03% | -0.38% |
| ruff | -28.08% | -28.23% | +0.20% |
| simd | -16.36% | -18.35% | -1.20% |
| tls | -0.34% | +0.72% | +0.71% |
| allocator | -0.58% | -0.33% | -0.61% |
| fre-forward_middle_hit | -28.57% | -28.61% | +2.18% |
| fre-forward_single | -29.44% | -29.49% | -2.08% |
| fre-forward_range | -21.52% | -22.95% | +1.18% |
| fre-packed-literal-set | -29.02% | -29.39% | -0.81% |
| nushell-type-relations | -15.16% | -18.42% | +0.82% |

Negative changes are faster. Values are median paired changes across six alternating pairs following a warmup pair. Both compute cases improve in all six timed pairs, with matching CPU reductions. These shared-host measurements are descriptive; small startup-dominated controls are mixed and noisy. Marginal time medians do not necessarily reproduce the median paired percentages.

All 308 public comparison commands (including 44 warmup commands) preserve expected stdout, logical instruction counts and peak guest memory on identical frozen artifacts. The screen requires at least 10% improvement on pgrust or Ruff, no compute-interpreter wall/CPU regression above 5%, and no JIT wall/CPU regression exceeding both 5% and 5ms. The five additional cases use that material-regression guard in both engines. All public comparison performance gates pass.

Correctness: 297 workspace tests pass in debug and release, with one ignored in each. Existing independent expected profiles cover mixed calls/backedges; other tests sweep budgets through native exits, faults, falloff, register growth, TLS resets and nested callbacks. A separate review found every storage-changing path leaves the inner loop, while per-op budgets, profiles, PC updates, call-proof indexing and JIT fallback behavior remain equivalent.

Ten fixed native-oracle division/remainder fixtures also pass for signed and unsigned 8/16/32/64/128-bit operands in both engines: 280 commands including 40 warmups. These supplement the boundary tests; narrow checksum collisions mean they are not a proof alone. Across all three runs, 588 commands preserve outputs, instruction counts and peak guest memory, and all frozen inputs remain unchanged.

This measures saved-bytecode process execution including VM startup. Export, compilation, linking, complete edit/build/test latency and unknown holdouts were not measured. Historical immutable tool 9637b0ac and its end-to-end results remain separate. No guest names or inputs select runtime behavior. No unrelated worktree, workload or cache was controlled.

A separate unsafe register-access candidate improved pgrust by 7.26% and Ruff by 9.858%, missing its fixed 10% gate. It is preserved locally as b04bbcb on experiment/validated-registers-20260912; its failed screen was not repeated unchanged. This frame-loop candidate retains checked register accesses.

The measured runner waits boundedly for the shared benchmark lock before starting children. The Python suite passes 21 tests, including three lock-wait tests. Source snapshots, binaries, exact build/test commands, all raw child receipts and harness snapshots remain under the isolated worktree’s .work/perf-general-20260912. Committed summaries retain hashes and absolute evidence paths.

[Screen](screen-summary.json) · [Screen gates](screen-assessment.json) · [Confirmation](confirmation-summary.json) · [Confirmation gates](confirmation-assessment.json) · [Native-oracle checks](native-oracles-summary.json) · [Build/test provenance](qualification.json) · [Predeclared plan](predeclared-plan.md) · [Source review](source-review.md).
