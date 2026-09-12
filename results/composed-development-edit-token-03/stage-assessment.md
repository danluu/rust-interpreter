# Combined engine: token

All132 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Median paired complete-command wall change -4.91%; CPU -8.61%. Descriptive A/A envelopes: 3.29% wall, 3.67% CPU. These are not confidence intervals.

Candidate/ordinary native paired wall ratio 2.140; candidate/line-tables native 2.362. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 6.118s | 9.106s | 1.770s | 0.720s | 0.854s | 4.229s |
| duplicate | 6.268s | 9.192s | 1.777s | 0.716s | 0.852s | 4.323s |
| candidate | 5.847s | 8.318s | 1.647s | 0.708s | 0.734s | 3.938s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.183s, template decoding 0.041s, cache load 0.034s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`, duplicate `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`, candidate `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 4.169s | 3.868s | 0.948 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.889s | 2.431s | 0.851 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.107s | 0.096s | 0.895 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.086s | 0.104s | 1.183 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.029s | 0.027s | 0.943 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
