# Repeated edits with stronger native controls

The custom engine still has a substantial compute gap. Token-phrase takes 6.664 s versus 2.002 s native; folded-trie takes 2.485 s versus 1.638 s. The five frontend/link dominated batches favor the custom engine under this specified control. These are selected original test batches, not whole-codebase development qualification.

Current source is Git `a2a0e04`, tool `b2aa6efe`; the paired engine is `57a54edd`. The source change fixes codegen-limit handling and thread/safety contracts. This run establishes working control comparisons for those workflows; it does not establish a runtime improvement from that fix.

## Complete edited commands

Each row contains five cumulative production-body edits repeated through three source cycles: fifteen edited commands per mode. Medians include launcher, Cargo/compiler/exporter work, linking where applicable, and test execution. Ratio is custom/native. No unchanged build enters these medians.

### Material guest execution

| Workflow | Native | Custom JIT | Ratio | Check reference |
| --- | ---: | ---: | ---: | ---: |
| [folded-literal-trie](../native-controls-corpus-01-folded-literal-trie/summary.json) | 1.638 s | 2.485 s | 1.52× | 0.636 s |
| [token-phrase](../native-controls-corpus-01-token-phrase/summary.json) | 2.002 s | 6.664 s | 3.33× | 0.684 s |
| [forward-anchored-tls](../native-controls-corpus-01-forward-anchored-tls/summary.json) | 1.544 s | 1.165 s | 0.75× | 0.728 s |
| [pgrust-sha1-inline8](../native-controls-corpus-01-pgrust-sha1-inline8/summary.json) | 0.756 s | 0.756 s | 1.00× | 0.393 s |

### Frontend/link dominated batches

| Workflow | Native | Custom JIT | Ratio | Check reference |
| --- | ---: | ---: | ---: | ---: |
| [pgrust](../native-controls-corpus-01-pgrust/summary.json) | 0.683 s | 0.504 s | 0.74× | 0.390 s |
| [nushell](../native-controls-corpus-01-nushell/summary.json) | 0.646 s | 0.431 s | 0.67× | 0.271 s |
| [rg-aot](../native-controls-corpus-01-rg-aot/summary.json) | 0.537 s | 0.196 s | 0.37× | 0.091 s |
| [ruff](../native-controls-corpus-01-ruff/summary.json) | 5.760 s | 3.007 s | 0.52× | 2.720 s |
| [nushell-type-relations](../native-controls-corpus-01-nushell-type-relations/summary.json) | 8.303 s | 4.704 s | 0.57× | 4.069 s |

## Controls and verification

Native used explicit root dev/test O0 and incremental settings, 18 Cargo jobs, default libtest concurrency, and no extra compiler flags. Manifest package overrides remain in effect. Custom builds used four jobs and the per-workflow MIR/inlining/runtime settings in the [frozen plan](summary.json). This qualifies one native configuration; linker/backend/compiler-worker alternatives remain unqualified. Previous stock-profile results were taken at a different time and do not isolate the effect of these settings.

The separate `cargo check --lib --profile test` target used the native profile, flags and jobs with its own cache. It ran after each three-mode group, without executing tests; even the intentionally wrong runtime edit checked successfully. Its time is an independent reference, not a strict lower bound or a subtractable component of another command.

All 756 commands completed: 567 primary build/test commands and 189 checking controls. The primary commands include 405 edited samples, 81 expected wrong-edit failures, 27 initial commands and 54 source-reverting cycle anchors. All original assertions and selections were preserved; 378 saved custom artifacts were hash-verified and corresponding engines received identical bytecode. Mode positions were balanced across the three edit cycles. [Final verification](final-verification.json) confirms report hashes and restored pinned source for all five projects.

Toolchain, fetched dependencies and shared std-MIR setup precede the initial commands. Initial target builds and later source-reverting anchors are recorded separately; OS caches were not cleared. Guest limits, trap settings and normal-try callback handling remain explicit in each report. These batches do not provide complete libtest, unwinding, OS/FFI or threading support.

## Variation and unresolved identity

All samples remain. Cross-cycle artifact identity differs in the three fre workflows; within-cycle engine pairs match exactly. The previous typed comparison found changed constant/data layout and immediate values, but did not prove cross-history semantic equivalence or identify the cause. No byte normalization or sample exclusion was used here.

Token cycle 0, state 2 took 10.421 s in the candidate versus 7.425 s in the baseline; child CPU was 9.015 versus 6.767 s. Execution contributed 7.344 versus 5.203 s, and Cargo 2.912 versus 1.931 s. Guest instruction counts differed by only 81,213 out of about 13.369 billion; emitted byte counts and compiled-function counts matched, with no codegen declines. A large change in guest instruction count does not explain this outlier. The cause remains unresolved; increased CPU means it cannot simply be described as time spent descheduled.

The second Nushell batch also varied substantially across cycles, including its native and checking commands. Per-edit ranges, CPU and load records are retained. Load samples include our own recent work and do not attribute contention to another process. No unrelated work was controlled to make this host idle. Three cycles do not supply a universal noise threshold or a significance guarantee.

Candidate-minus-baseline paired medians below describe the codegen-limit comparison. Negative values favor the candidate. They are not used to select another small runtime optimization.

| Workflow | Wall delta | Child CPU delta |
| --- | ---: | ---: |
| pgrust | +0.3 ms | +0.1 ms |
| nushell | -6.3 ms | -3.5 ms |
| rg-aot | +1.1 ms | +0.7 ms |
| folded-literal-trie | -28.1 ms | -32.6 ms |
| token-phrase | +65.2 ms | +44.9 ms |
| forward-anchored-tls | -3.9 ms | -0.1 ms |
| pgrust-sha1-inline8 | -0.1 ms | +0.3 ms |
| ruff | -67.2 ms | -18.9 ms |
| nushell-type-relations | -34.0 ms | -20.4 ms |

## Next decision

Keep the codegen-limit correctness fix, with its [202 passing workspace tests](../review-codegen-limits-01/summary.json). The older 47,004 native differential commands, TLS checks and 382-body fre replay remain evidence for `57a54edd`; they have not been rerun for this fix.

Use the [typed native-call census](../native-call-census-01/summary.json) and [ABI requirements](../../docs/NATIVE-CALL-EXPERIMENT.md) to choose a larger call transition experiment. Strict leaves alone cover little of the measured call/frame work. Explicit terminal trap handling and nested calls need separate accounting before choosing between a bounded call-tree path and a general continuation ABI. Profile shares and call counts are not predicted speedups.
