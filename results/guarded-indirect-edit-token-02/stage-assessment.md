# Combined engine: token

All154 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Versus wide-operation baseline: paired complete-command wall change -1.44%; CPU -0.97%. Descriptive A/A envelopes: 4.75% wall, 3.28% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 1.0331/1.0231. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -12.44%; CPU -13.98%.

Candidate/ordinary native paired wall ratio 1.768; candidate/line-tables native 1.983. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.838s | 7.174s | 1.513s | 0.634s | 0.683s | 3.209s |
| duplicate | 4.801s | 7.093s | 1.519s | 0.632s | 0.695s | 3.146s |
| candidate | 4.727s | 7.029s | 1.517s | 0.637s | 0.685s | 3.114s |
| anchor | 5.573s | 8.246s | 1.674s | 0.659s | 0.806s | 3.688s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.181s, template decoding 0.043s, cache load 0.035s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `9e219e2ecb7cc05b2946f30467b9f3d0886e676355d50dcabf94740a82864c2c`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 3.137s | 3.046s | 0.987 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.236s | 2.218s | 0.990 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.097s | 0.096s | 0.987 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.077s | 0.075s | 0.979 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.021s | 0.021s | 0.987 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
