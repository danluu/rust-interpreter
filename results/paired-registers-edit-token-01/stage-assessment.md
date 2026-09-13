# Combined engine: token

All154 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Versus wide-operation baseline: paired complete-command wall change -0.71%; CPU -0.09%. Descriptive A/A envelopes: 1.77% wall, 1.56% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 1.0106/1.0147. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -11.85%; CPU -13.59%.

Candidate/ordinary native paired wall ratio 1.790; candidate/line-tables native 2.088. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.958s | 7.291s | 1.580s | 0.695s | 0.684s | 3.272s |
| duplicate | 5.040s | 7.377s | 1.599s | 0.670s | 0.708s | 3.327s |
| candidate | 4.945s | 7.277s | 1.564s | 0.671s | 0.682s | 3.247s |
| anchor | 5.522s | 8.359s | 1.645s | 0.656s | 0.770s | 3.762s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.157s, template decoding 0.042s, cache load 0.032s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `7cc4b8989ebefb19c153c33f384a200af392ff228d9c84ab4a4fdc17d7c0891a`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 3.200s | 3.176s | 0.988 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.282s | 2.305s | 1.009 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.097s | 0.098s | 1.005 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.080s | 0.079s | 0.999 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.022s | 0.022s | 1.004 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
