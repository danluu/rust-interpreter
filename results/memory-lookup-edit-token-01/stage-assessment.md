# Combined engine: token

All154 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus wide-operation baseline: paired complete-command wall change -7.66%; CPU -6.78%. Descriptive A/A envelopes: 5.25% wall, 3.94% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 0.9758/0.9715. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -18.35%; CPU -17.88%.

Candidate/ordinary native paired wall ratio 1.894; candidate/line-tables native 2.086. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.845s | 7.365s | 1.373s | 0.552s | 0.629s | 3.324s |
| duplicate | 4.758s | 7.366s | 1.372s | 0.555s | 0.621s | 3.320s |
| candidate | 4.548s | 6.979s | 1.357s | 0.552s | 0.612s | 3.077s |
| anchor | 5.511s | 8.430s | 1.506s | 0.554s | 0.752s | 3.861s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.124s, template decoding 0.037s, cache load 0.030s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`. Every edited candidate lookup is a validated hit. The composition changes both the VM and launcher lookup versus the wide control.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `f0af2e3e4c1093fd0e7bb5a5a53dd8e72b305d7e1536ea9c4b999ba2acaa965a`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 3.257s | 3.008s | 0.899 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.318s | 2.222s | 0.961 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.099s | 0.098s | 0.977 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.079s | 0.076s | 0.947 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.022s | 0.022s | 0.975 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
