# Inline checked scalar memory operations

The candidate passes the predeclared public runtime screen and five additional workload checks. It forces inlining of Memory::range, Memory::load and Memory::store; every method body, memory check, error and generic-width fallback is unchanged. The retained frame-loop VM f33b40d is the baseline.

| Workload | Interpreter wall change | Interpreter CPU change | JIT wall change |
|---|---:|---:|---:|
| pgrust | -6.65% | -6.65% | +0.79% |
| nushell | -0.37% | -0.99% | +0.78% |
| ruff | -0.99% | -1.02% | +2.18% |
| simd | -4.03% | -4.13% | -0.42% |
| tls | -1.17% | +1.34% | +0.48% |
| allocator | +3.67% | +3.70% | +4.91% |
| fre-forward_middle_hit | -4.81% | -4.76% | -0.67% |
| fre-forward_single | -5.00% | -5.00% | +1.53% |
| fre-forward_range | -2.09% | -2.34% | -2.58% |
| fre-packed-literal-set | -2.66% | -2.88% | -0.96% |
| nushell-type-relations | +0.11% | -0.57% | -0.61% |

Negative changes are faster. Values are medians of six alternating paired changes after a warmup pair. Pgrust improves in all six timed pairs; Ruff improves in only three, so its small median change is not a strong speedup result. Four additional Fre cases improve 2.1–5.0%; Nushell type relations is essentially unchanged. Tiny startup controls are noisy. These shared-host measurements are descriptive, without confidence intervals. JIT passes regression guards; no general JIT speedup is claimed.

The prospectively fixed gate requires at least 5% interpreter wall improvement on pgrust or Ruff, no compute-interpreter wall/CPU regression over 5%, and no JIT wall/CPU regression exceeding both 5% and 5ms. The five additional cases use that material-regression guard in both engines. All public performance gates pass. All 308 public comparison commands (44 warmups) preserve stdout, logical instruction counts and peak guest memory on identical frozen artifacts.

Assembly confirms that common 1/2/4/8/16-byte loads/stores no longer call range/load/store helpers or pass successful scalar/range results through stack temporaries. Generic-width copy scratch remains. The pure interpreter function grows from 10,496 to 12,288 bytes including alignment; its fixed VM stack grows from 1,200 to 1,232 bytes, while scalar helper frames disappear on common paths. Completion still reloads frame pointer and register count. The executable grows by 32,480 bytes. These are code-generation observations, not attribution of measured savings.

Inlining only load/store was a distinct earlier candidate, preserved locally as 2a976e5 on experiment/scalar-inline-20260912. It moved the remaining call boundary into range and regressed pgrust 2.0% and Ruff 5.5%, failing its original gates. That failed binary was not rerun unchanged. The final candidate also inlines range; both original source snapshots, binaries and decisions remain available.

Correctness: all 297 workspace tests pass in debug and release, with one ignored in each. Existing tests cover all scalar sizes, alignments, both arenas, boundaries, read-only/invalid accesses, copy/fill/allocation uses of range, instruction budgets and native/TLS transitions. The Python suite previously passed 21 tests, including three lock-wait checks. All candidate runs used the same frozen harness (SHA256 `bd83cf3c908c4026eb9a79cff200360ef301deda64ba66f67ec7484a31112923`), preserved as `harness.py` in each raw run directory. A subsequent upstream merge adds engine selection with the same both-engine default and creates the output directory after acquiring the lock; those changes were not part of the measured runs.

All 280 commands on ten signed/unsigned native-oracle fixtures pass, covering integer widths 8/16/32/64/128 in both engines. Outputs agree with independently computed native Rust results, with unchanged instruction counts, peak guest memory and frozen inputs. These checks supplement boundary tests; narrow checksums alone are not a proof of correctness. Across the public and oracle runs, all 588 commands pass, including 84 warmups.

This qualifies saved-bytecode process runtime including VM startup. Export, frontend, linking, complete edit/build/test latency and unknown holdouts were not measured. Improvements are relative to f33b40d, not cumulative estimates from earlier experiments. The historical immutable tool 9637b0ac and its end-to-end results remain separate. No workload name or input value selects implementation behavior; no unrelated workloads, worktrees or caches were controlled.

Exact source/patch snapshots, immutable binaries, build/test receipts, all raw child commands and measured harness/disassembly snapshots remain in the isolated worktree’s .work/perf-general-20260912. Committed provenance and plans retain absolute paths and hashes.

[Predeclared plan](predeclared-plan.md), [screen](screen-summary.json), [screen gate](screen-assessment.json), [confirmation](confirmation-summary.json), [confirmation gate](confirmation-assessment.json), [native-oracle checks](native-oracles-summary.json), [code generation](code-generation-review.md), [source/build provenance](qualification.json).

Integration with upstream `4f6fc2e` preserves the exact qualified Rust source, Cargo configuration and toolchain. The merged Python suite passes all 21 tests. Its separate receipt and current harness hash are recorded in [qualification.json](qualification.json); measured-harness hashes remain tied to the original runs.
