# Current measured status

Retained build **5b2330c/9637b0ac**: custom interpreter and direct AArch64 JIT, strict rustc type/borrow checking. The exec Cargo wrapper is deployed.

The retained measurements put folded near the specified native control and token about 2.3× slower. Other selected workflows save code-generation/link time while executing their original assertions. Native uses project debuginfo/link settings; fre debuginfo calibration selected no replacement preset. Large native controls and full libtest compatibility remain open.

Times below come from each row’s own three-cycle, five-edit history. Native uses O0/incremental, 18 jobs/default test threads; custom uses four jobs. Cold means empty per-mode caches, excluding tool/sysroot bootstrap and OS cache coldness.

| Workflow | Warm native | Warm custom | Cargo check | Custom/check | Cold native | Cold custom |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| [folded-literal-trie](results/aggregate-relocation-e2e-01-folded-literal-trie/summary.json) | 1.702s | 1.696s | 0.632s | 2.68× | 6.626s | 6.031s |
| [token-phrase](results/aggregate-relocation-e2e-01-token-phrase/summary.json) | 1.965s | 4.462s | 0.644s | 6.93× | 6.639s | 9.030s |
| [nushell-type-relations](results/aggregate-relocation-heldout-01-nushell-type-relations/summary.json) | 7.529s | 4.066s | 3.595s | 1.13× | 39.698s | 72.023s |
| [ruff](results/aggregate-relocation-heldout-01-ruff-retry-01/summary.json) | 5.259s | 2.998s | 2.641s | 1.14× | 26.019s | 28.332s |
| [nushell](results/aggregate-relocation-heldout-01-nushell/summary.json) | 0.657s | 0.448s | 0.292s | 1.54× | 16.171s | 19.648s |
| [forward-anchored-tls](results/aggregate-relocation-heldout-01-forward-anchored-tls/summary.json) | 1.510s | 1.005s | 0.645s | 1.56× | 6.606s | 5.578s |
| [pgrust-sha1-inline8](results/aggregate-relocation-heldout-01-pgrust-sha1-inline8/summary.json) | 0.810s | 0.638s | 0.382s | 1.67× | 1.102s | 0.650s |
| [pgrust](results/aggregate-relocation-heldout-01-pgrust/summary.json) | 0.678s | 0.470s | 0.384s | 1.22× | 0.762s | 0.459s |
| [rg-aot](results/aggregate-relocation-heldout-01-rg-aot/summary.json) | 0.564s | 0.191s | 0.095s | 2.01× | 3.996s | 2.816s |

Custom cold commands are slower on 4 of 9 rows. Cargo check executes no tests; custom/check is a descriptive overhead comparison, not a causal subtraction. Paired changes establish version comparisons; cross-session absolute medians do not.

Current source also includes [general interpreter arithmetic and scalar-memory improvements](results/general-interpreter-20260912/assessment.md): 297 debug/release tests pass (one ignored), and 308 saved-artifact comparisons preserve outputs, instruction counts and peak memory. Those runtime measurements exclude export/build costs; the complete-workflow anchor above remains separate.

Retained qualification: 289 debug/release tests (one ignored), 47,004 broad validation commands, 245 TLS/destructor commands and 382 fre body passes (seven ignored). Seven held-out histories passed separate 5% wall/CPU regression guards. Private results expose aggregates only.

The lightweight wrapper is in the retained build despite failing its standalone cold-performance gate. Budget-register, call-slot and whole-call candidates remain parked. A new 18-custom-worker latency preset is on the development branch; it does not alter the measurements above.

**Latest scalar ABI screen: parked.** Five real edits per case, original tests and wrong-edit controls; all correctness checks passed.

| Workload | Paired wall change | Paired CPU change |
| --- | ---: | ---: |
| token-phrase | -0.74% | -2.66% |
| folded-literal-trie | -0.41% | +1.07% |

Token missed the 8% screening target. Execution saved about 170ms paired while Cargo added 144ms. Full scalar A/A and held-outs are stopped. Source lives under `crates/` on `experiment/scalar-value-abi` (measured commit `840fdb5`); the timing tool used the same wrapper on both sides.

[Scalar assessment](results/scalar-edit-smoke-01/assessment.md).

**Latest exporter attribution:** seven real token artifacts match the retained compiler exactly. Graph lowering costs 691ms; hashing 49ms, publication 30ms, serialization 14ms and validation 5ms. [Assessment](results/export-costs-token-02/assessment.md).

Effective profiles are recorded for all five projects: pgrust/Ruff already use line tables; all use unpacked split debuginfo. [Native stage attribution](results/native-existing-stages-01/assessment.md) covers 135 existing edited commands.

[Fre native calibration](results/native-tuned-calibration-01/assessment.md) was inconclusive: line tables saved 7.86%, below its fixed 8% screen; debug=0 saved 5.17%. All 21 Cargo commands and 15 diagnostic repeats had the expected assertion outcomes. No new native preset was selected.

The [unfiltered fre command](results/fre-unfiltered-native-01/assessment.md) passed 382 unit and 52 integration tests (seven ignored), then failed a doc test whose expected diagnostic code was absent. The root launcher now runs all 52 original integration assertions across 10 targets with shared dependency metadata. [Coverage](results/fre-integration-targets-02/assessment.md).

The [integration edit pilot](results/fre-integration-edit-01/assessment.md) records five real edits: custom 0.816s, native 1.015s, Cargo check 0.539s; paired wall -20.4%. Both sides use 18 jobs. This one-cycle pilot is separate from the retained histories above.

The [compute-heavy integration target](results/fre-integration-es8-edit-01/assessment.md) costs 3.867s custom versus 1.449s native (2.678× paired), with check at 0.529s. All 24 edit/restoration controls pass. Native uses default test threads; custom runs its two bodies sequentially. Generated execution dominates the [profile](results/fre-integration-es8-sample-01/assessment.md).

[Source restoration now refreshes modification time](results/source-restore-after-01/assessment.md) so Cargo rebuilds the restored original. Actual Cargo regressions and 18 Python tests pass. Remaining original-source bytecode differences keep export determinism open.

**Fixed frame clearing: parked.** The fresh combined es8 confirmation improves complete-command wall by 7.39% and CPU by 7.61%, missing the required 8% wall gate. All 96 commands and 15 edited pairs pass correctness and restoration controls. The earlier isolated-source confirmation passed at 8.37% wall; 8 of 9 original library gates passed. The remaining comparisons are canceled. Broad combined correctness passes 300 debug/release tests (one ignored), 47,004 native differential commands, 245 TLS checks, 382 fre bodies (seven ignored) and 52 integration assertions. The runtime stays off main. [Decision](results/fixed-frame-clear-combined-01/assessment.md).

**Open adoption work:** tuned native controls; complete test-suite execution; unwinding, threads and general OS/FFI; deterministic/reusable export graphs. Selected test-body results are not whole-project qualification.

**Next:** Uninstrumented selection is qualified on main. Split-arena address checks pass363tests/profile and42real-suite commands but regress token2.51%; the candidate is parked without retiming. Next add seeded valid-program differential coverage for loops, calls, aliases and budgets before more structural runtime work.

[Review decisions](docs/SUGGESTIONS-REVIEW-20260911.md) · [Work state](STATE.md) · [Evidence index](results/INDEX.md) · [Retention policy](results/RETENTION.md)

Generated by `python3 scripts/update_status.py` from `benchmarks/current-status.json` and the linked receipts.
