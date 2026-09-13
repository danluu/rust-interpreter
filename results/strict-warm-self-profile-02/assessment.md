# Strict warm-build self-profile diagnosis

Edit 2 in `nushell` / `type-relations` passed all 14 original tests, as did restoration. This is a warm continuation of [profile 01](../strict-warm-profile-01/assessment.md), with its existing target directory. The source hash was fresh relative to the recorded edit history; the cold prime was skipped. This is not an independent cold history, a speedup comparison, or acceptance of the 0.5 s target.

| State | Cargo wall s | VM wall s | rustc self-profile | Tests |
| --- | ---: | ---: | --- | --- |
| edited | 9.909496 | 0.037811 | self | 14 passed |
| restored | 5.604304 | 0.012538 | off | 14 passed |

The edited and restored commands have different source and cache states. Their wall-time difference does not estimate profiling overhead. Both use the diagnostic wrapper, Cargo timings and exporter timers; only the edited command records rustc self-profiles. These direct Cargo and VM intervals exclude launcher startup, preflight and tool/bootstrap setup.

The edited build has 18 compiler invocations, 1 build-script execution and 5 compiler information probes: 19 timed Cargo units. Every real compiler invocation has a retained raw profile and a successful saved reader result.

## How to read the query data

Self time subtracts directly nested events on the same thread; inclusive time includes those nested events. Incremental-load and hashing times are already represented in self time, so they are not additional costs to add. The reader’s `total_time` is the sum of each recorded thread’s end-minus-start span. These are elapsed-event counters, not measured process CPU time. Concurrent threads and compiler invocations overlap; neither their spans nor inclusive query rows sum to complete-command wall time.

`Invocations` counts actual query/provider or activity executions without cache hits. Loads and blocked hits do not increment that counter; zero invocations can coexist with substantial load time. Cache misses and cache hits remain separate counters in the JSON; activity rows need not have query-cache semantics.

## All edited compiler units

Roles preserve host/target context and features in the JSON. The selected test is identified through its captured exporter arguments and selected Cargo artifact, including its test configuration; the initial wrapper argv alone does not contain `--test`.

| Package | Role | Child wall s | Sum of thread spans s | Raw profile bytes |
| --- | --- | ---: | ---: | ---: |
| nu-protocol | ordinary library check | 1.618996 | 1.593545 | 67256134 |
| nu-protocol | host library build | 3.610094 | 5.580467 | 95568661 |
| nu-engine | ordinary library check | 0.369259 | 0.333523 | 10974711 |
| nu-heavy-utils | ordinary library check | 0.303828 | 0.267870 | 8608288 |
| nu-json | ordinary library check | 0.222867 | 0.189634 | 6975294 |
| nu-parser | ordinary library check | 0.390003 | 0.357228 | 11772706 |
| nu-color-config | ordinary library check | 0.142844 | 0.113475 | 4027392 |
| nu-table | ordinary library check | 0.192803 | 0.164182 | 6036712 |
| nuon | ordinary library check | 0.163744 | 0.132781 | 3927930 |
| nu-cmd-base | ordinary library check | 0.137894 | 0.106617 | 3635935 |
| nu-cmd-lang | ordinary library check | 0.351584 | 0.318008 | 8626220 |
| nu-command | ordinary library check | 2.333229 | 2.284862 | 68863248 |
| nu-std | ordinary library check | 0.117487 | 0.088373 | 2040923 |
| nu-cmd-extra | host build-script compilation | 0.709642 | 0.754163 | 4656251 |
| nu-cmd-extra | ordinary library check | 0.296453 | 0.264461 | 10186823 |
| nu-cli | ordinary library check | 0.440808 | 0.395320 | 16095384 |
| nu-test-support | ordinary library check | 0.498330 | 0.446768 | 12658282 |
| nu-protocol | selected library test check | 2.501152 | 2.428756 | 76161804 |

## Four longest compiler invocations

Rows below are the ten largest self-time labels within each invocation. A row can aggregate many events. The full query table, including exact nanosecond durations and all counts, is preserved in the compressed query archive.

### nu-protocol — host library build

Compiler child wall: 3.610094 s; sum of recorded thread spans: 5.580467 s.

| Label | Self s | Inclusive s | Incremental load s | Invocations | Cache misses | Cache hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `LLVM_passes` | 1.121397 | 1.121397 | 0.000000 | 1 | 1 | 0 |
| `LLVM_module_codegen_emit_obj` | 0.622037 | 0.622037 | 0.000000 | 46 | 46 | 0 |
| `codegen_module` | 0.426786 | 0.804312 | 0.000000 | 46 | 46 | 0 |
| `link_rlib` | 0.317635 | 0.317635 | 0.000000 | 1 | 1 | 0 |
| `codegen_crate` | 0.315425 | 1.138857 | 0.000000 | 1 | 1 | 0 |
| `codegen_copy_artifacts_from_incr_cache` | 0.165597 | 0.165597 | 0.000000 | 210 | 210 | 0 |
| `expand_proc_macro` | 0.140833 | 0.140833 | 0.000000 | 308 | 308 | 0 |
| `generate_crate_metadata` | 0.134048 | 0.663554 | 0.000000 | 1 | 1 | 0 |
| `typeck_root` | 0.129120 | 0.170104 | 0.122295 | 15 | 15 | 10128 |
| `lower_to_hir` | 0.115964 | 0.156661 | 0.000000 | 28758 | 28758 | 65110 |

### nu-protocol — selected library test check

Compiler child wall: 2.501152 s; sum of recorded thread spans: 2.428756 s.

| Label | Self s | Inclusive s | Incremental load s | Invocations | Cache misses | Cache hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `expand_proc_macro` | 0.391138 | 0.391138 | 0.000000 | 966 | 966 | 0 |
| `expand_crate` | 0.295755 | 0.832410 | 0.000000 | 1 | 1 | 0 |
| `lower_to_hir` | 0.251869 | 0.332831 | 0.000000 | 28327 | 28327 | 77130 |
| `typeck_root` | 0.203306 | 0.262250 | 0.115840 | 90 | 90 | 8534 |
| `late_resolve_crate` | 0.119315 | 0.123600 | 0.000000 | 1 | 1 | 0 |
| `incr_comp_load_dep_graph` | 0.091023 | 0.091023 | 0.000000 | 1 | 1 | 0 |
| `metadata_register_crate` | 0.085302 | 0.325216 | 0.000000 | 455 | 455 | 0 |
| `incr_comp_encode_dep_graph` | 0.065862 | 0.065862 | 0.000000 | 1115524 | 1115524 | 0 |
| `trait_impls_of` | 0.049737 | 0.074484 | 0.000000 | 193 | 193 | 9582 |
| `encode_query_results_for` | 0.048737 | 0.048737 | 0.000000 | 58 | 58 | 0 |

### nu-command — ordinary library check

Compiler child wall: 2.333229 s; sum of recorded thread spans: 2.284862 s.

| Label | Self s | Inclusive s | Incremental load s | Invocations | Cache misses | Cache hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `expand_crate` | 0.263840 | 0.531804 | 0.000000 | 1 | 1 | 0 |
| `metadata_register_crate` | 0.183637 | 0.501083 | 0.000000 | 419 | 419 | 0 |
| `incr_comp_load_dep_graph` | 0.143869 | 0.143869 | 0.000000 | 1 | 1 | 0 |
| `generate_crate_metadata` | 0.140955 | 0.394485 | 0.000000 | 1 | 1 | 0 |
| `lower_to_hir` | 0.135795 | 0.191491 | 0.000000 | 19608 | 19608 | 44666 |
| `metadata_decode_entry_module_children` | 0.131193 | 0.131193 | 0.000000 | 4125 | 4125 | 0 |
| `optimized_mir` | 0.130820 | 0.130820 | 0.130820 | 0 | 0 | 0 |
| `typeck_root` | 0.118685 | 0.202222 | 0.054368 | 21 | 21 | 1715 |
| `incr_comp_garbage_collect_session_directories` | 0.103269 | 0.103269 | 0.000000 | 1 | 1 | 0 |
| `late_resolve_crate` | 0.093476 | 0.138766 | 0.000000 | 1 | 1 | 0 |

### nu-protocol — ordinary library check

Compiler child wall: 1.618996 s; sum of recorded thread spans: 1.593545 s.

| Label | Self s | Inclusive s | Incremental load s | Invocations | Cache misses | Cache hits |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `expand_proc_macro` | 0.174472 | 0.174472 | 0.000000 | 308 | 308 | 0 |
| `typeck_root` | 0.149283 | 0.176515 | 0.133144 | 15 | 15 | 10128 |
| `metadata_register_crate` | 0.126932 | 0.429079 | 0.000000 | 183 | 183 | 0 |
| `expand_crate` | 0.110315 | 0.460420 | 0.000000 | 1 | 1 | 0 |
| `lower_to_hir` | 0.105809 | 0.147162 | 0.000000 | 28758 | 28758 | 65110 |
| `incr_comp_load_dep_graph` | 0.090039 | 0.090039 | 0.000000 | 1 | 1 | 0 |
| `generate_crate_metadata` | 0.087131 | 0.203021 | 0.000000 | 1 | 1 | 0 |
| `late_resolve_crate` | 0.058685 | 0.067438 | 0.000000 | 1 | 1 | 0 |
| `encode_query_results_for` | 0.056191 | 0.056191 | 0.000000 | 58 | 58 | 0 |
| `optimized_mir` | 0.041099 | 0.041575 | 0.040759 | 2 | 2 | 0 |

In the selected test compilation, procedural macros account for 0.391138 s self time; HIR lowering accounts for 0.251869 s self time. The `typeck_root` row includes 0.115840 s of incremental-result loading. These are distinct required frontend activities, not a demonstrated removable budget.

The changed production edit also reaches the host `nu-protocol` build: 46 LLVM object-emission events and 46 `codegen_module` events show work on that many codegen units. This generic-code change therefore includes substantial host code generation and LLVM work; the table is not solely a selected-test frontend profile. The counters identify work observed here, not the causal cost of each source change.

## Evidence and reproduction

Source revision: `9d3157963241cf89447119d34d6e887859f5e7e8`. Tool key: `923ad6d94c365365f15322ee65d32dca6ba9ccc4fd07a8147111329ea1955c86`. Reader: measureme 12.0.3, recorded source commit `5ac839c602b59eee9c908b3b35b6d6c0cd1c42f7`. The compiler is the pinned nightly-2026-09-08 build; its full version and sysroot identity are retained in the JSON.

[summary.json](summary.json) preserves both source states, all test outcomes, exact source/tool/sysroot/harness identities, all 18 compiler roles, raw-profile paths/sizes/hashes and archive hashes. [query-summaries.json.gz](query-summaries.json.gz) preserves the exact UTF-8 bytes of all saved reader JSON files, successful reader commands, supervisor/build receipts and the reader analysis source used to interpret counters. [report.json.gz](report.json.gz) preserves the exact original diagnostic report, including compiler arguments. All archived member hashes and gzip round trips were verified; selected artifacts and both suites were validated against their recorded hashes. Raw `.mm_profdata` files stay in `.work` and are not copied into results.

Repackage the retained evidence into a fresh result directory without executing any workload:

```sh
python3 benchmarks/experiments/strict-warm-build/analyzer.py \
  .work/strict-warm-self-profile-02/report.json \
  --reader-build .work/strict-warm-build/measureme-build-01/summary.json \
  --run-id strict-warm-self-profile-02-reproduced
```
