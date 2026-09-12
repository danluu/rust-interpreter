# Combined engine: token

All154 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Versus integrated baseline: paired complete-command wall change -0.55%; CPU -0.39%. Descriptive A/A envelopes: 4.65% wall, 3.93% CPU. These are not confidence intervals.

Versus fixed selected-suite anchor: wall -7.34%; CPU -9.83%.

Candidate/ordinary native paired wall ratio 2.188; candidate/line-tables native 2.371. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 5.373s | 8.124s | 1.404s | 0.564s | 0.642s | 3.844s |
| duplicate | 5.400s | 8.018s | 1.446s | 0.580s | 0.649s | 3.784s |
| candidate | 5.465s | 8.244s | 1.432s | 0.540s | 0.669s | 3.872s |
| anchor | 5.749s | 8.882s | 1.540s | 0.570s | 0.799s | 4.073s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.139s, template decoding 0.041s, cache load 0.032s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, duplicate `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, candidate `2ad48ea7fd0d0c8a5d32e220b9c3997684d9952f13b8acd348fc59c3a6d026c3`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 3.777s | 3.795s | 0.993 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.461s | 2.511s | 1.007 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.102s | 0.103s | 0.990 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.094s | 0.093s | 0.973 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.026s | 0.026s | 1.001 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
