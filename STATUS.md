# Current measured status

Retained build **5b2330c/9637b0ac**: custom interpreter and direct AArch64 JIT, strict rustc type/borrow checking. The exec Cargo wrapper is deployed.

The retained measurements put folded near the specified native control and token about 2.3× slower. Other selected workflows save code-generation/link time while executing their original assertions. Native uses project debuginfo/link settings; alternatives have not been compared. Full libtest compatibility is unfinished.

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

The [unfiltered fre command](results/fre-unfiltered-native-01/assessment.md) passed 382 unit and 52 integration tests (seven ignored), then failed a doc test whose expected diagnostic code was absent. The 52 integration tests are outside the custom library replay. A [new integration-target selector](results/integration-targets-fixture-01/assessment.md) passes four unit checks and 14 Cargo/native/custom controls; original fre target qualification follows.

**Open adoption work:** tuned native controls; complete test-suite execution; unwinding, threads and general OS/FFI; deterministic/reusable export graphs. Selected test-body results are not whole-project qualification.

**Next:** Qualify original fre integration-test targets with the new explicit selector; preserve the native doc-test failure and check a large native control.

[Review decisions](docs/SUGGESTIONS-REVIEW-20260911.md) · [Work state](STATE.md) · [Evidence index](results/INDEX.md) · [Retention policy](results/RETENTION.md)

Generated by `python3 scripts/update_status.py` from `benchmarks/current-status.json` and the linked receipts.
