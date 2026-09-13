# Combined engine: token

All154 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus wide-operation baseline: paired complete-command wall change -6.60%; CPU -5.93%. Descriptive A/A envelopes: 1.82% wall, 0.53% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 0.9521/0.9460. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -17.82%; CPU -18.07%.

Candidate/ordinary native paired wall ratio 1.862; candidate/line-tables native 2.091. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.803s | 7.298s | 1.357s | 0.550s | 0.613s | 3.317s |
| duplicate | 4.825s | 7.278s | 1.341s | 0.545s | 0.611s | 3.292s |
| candidate | 4.503s | 6.876s | 1.343s | 0.549s | 0.604s | 3.000s |
| anchor | 5.393s | 8.347s | 1.482s | 0.549s | 0.746s | 3.821s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.128s, template decoding 0.038s, cache load 0.029s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `f0af2e3e4c1093fd0e7bb5a5a53dd8e72b305d7e1536ea9c4b999ba2acaa965a`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 3.250s | 2.933s | 0.902 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.289s | 2.198s | 0.957 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.097s | 0.096s | 0.990 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.082s | 0.073s | 0.891 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.023s | 0.020s | 0.903 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
