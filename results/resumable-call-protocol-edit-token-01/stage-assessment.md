# Combined engine: token

All154 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Versus corrected composition: paired complete-command wall change -1.62%; CPU -0.53%. Descriptive A/A envelopes: 3.81% wall, 3.68% CPU. These are not confidence intervals.

Versus fixed selected-suite anchor: wall -5.78%; CPU -9.54%.

Candidate/ordinary native paired wall ratio 2.031; candidate/line-tables native 2.196. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 5.529s | 7.985s | 1.648s | 0.707s | 0.734s | 3.767s |
| duplicate | 5.560s | 7.976s | 1.677s | 0.711s | 0.739s | 3.743s |
| candidate | 5.494s | 7.908s | 1.678s | 0.731s | 0.742s | 3.716s |
| anchor | 5.898s | 8.725s | 1.797s | 0.722s | 0.865s | 3.993s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.184s, template decoding 0.044s, cache load 0.037s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`, duplicate `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`, candidate `8f1070dbaa634e2d8cb9ac44936ed4114af7e399834c16c6bec31df9e1934dc0`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 3.689s | 3.641s | 0.988 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.381s | 2.367s | 0.990 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.100s | 0.101s | 1.005 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.094s | 0.091s | 0.971 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.026s | 0.025s | 0.961 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
