# Combined engine: token

All154 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus integrated baseline: paired complete-command wall change -4.55%; CPU -3.25%. Descriptive A/A envelopes: 2.39% wall, 1.70% CPU. These are not confidence intervals.

Versus fixed selected-suite anchor: wall -12.05%; CPU -12.66%.

Candidate/ordinary native paired wall ratio 1.957; candidate/line-tables native 2.166. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.890s | 7.293s | 1.290s | 0.523s | 0.591s | 3.411s |
| duplicate | 4.845s | 7.299s | 1.304s | 0.525s | 0.596s | 3.427s |
| candidate | 4.663s | 7.070s | 1.300s | 0.526s | 0.590s | 3.193s |
| anchor | 5.219s | 8.132s | 1.427s | 0.522s | 0.719s | 3.708s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.121s, template decoding 0.037s, cache load 0.029s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, duplicate `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, candidate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 3.345s | 3.126s | 0.936 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.245s | 2.253s | 1.003 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.096s | 0.096s | 1.002 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.084s | 0.078s | 0.928 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.023s | 0.022s | 0.928 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
