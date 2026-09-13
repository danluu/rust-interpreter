# Direct native operands: token

All 154 commands passed their expected outcomes: 12 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Versus adopted baseline: paired complete-command wall change +0.78%; CPU +0.06%. Descriptive A/A envelopes: 4.84% wall, 2.25% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 1.0561/1.0232. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -17.84%; CPU -18.62%.

Candidate/ordinary native paired wall ratio 1.773; candidate/line-tables native 2.027. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 4.675s | 6.918s | 1.495s | 0.649s | 0.650s | 3.016s |
| duplicate | 4.728s | 7.094s | 1.528s | 0.662s | 0.650s | 3.112s |
| candidate | 4.652s | 6.952s | 1.531s | 0.663s | 0.663s | 3.032s |
| anchor | 5.758s | 8.631s | 1.627s | 0.649s | 0.786s | 3.998s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 5218/204. Binding 0.156s, template decoding 0.039s, cache load 0.032s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`. Every edited candidate lookup is a validated hit. Baseline, duplicate and candidate share cached lookup and exact exporter/wrapper bytes; only the candidate VM changes.

Tool keys: baseline `e729a493261568d841d3ef212bcdfeef8fa4bf715cd26538f3cb9d1fa447e846`, duplicate `e729a493261568d841d3ef212bcdfeef8fa4bf715cd26538f3cb9d1fa447e846`, candidate `ac02a5e2986b5f57dacdebda1c277a096bddee3cbab522fc0eff50517279310c`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

The primary performance gate failed. Keep this runtime experimental; the other comparisons remain unstarted and this case will not be retimed.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 2.947s | 2.956s | 0.992 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2.229s | 2.221s | 0.997 |
| token_phrase::tests::anchor_route_rejects_endpoints_other_bytes_and_high_bytes | 0.096s | 0.096s | 1.002 |
| token_phrase::tests::maximal_tokens_preserve_restart_greediness_and_nonoverlap | 0.074s | 0.072s | 0.996 |
| token_phrase::tests::route_threshold_127_128_129_preserves_exact_semantics | 0.021s | 0.020s | 0.985 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
