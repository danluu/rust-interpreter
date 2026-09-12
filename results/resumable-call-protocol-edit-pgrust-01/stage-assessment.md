# Combined engine: pgrust

All154 commands passed their expected outcomes: 4 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus corrected composition: paired complete-command wall change +0.19%; CPU -0.06%. Descriptive A/A envelopes: 1.41% wall, 2.11% CPU. These are not confidence intervals.

Versus fixed selected-suite anchor: wall +1.05%; CPU +1.55%.

Candidate/ordinary native paired wall ratio 0.856; candidate/line-tables native 0.946. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.538s | 0.525s | 0.444s | 0.016s | 0.009s | 0.022s |
| duplicate | 0.538s | 0.523s | 0.444s | 0.016s | 0.009s | 0.022s |
| candidate | 0.542s | 0.528s | 0.447s | 0.016s | 0.009s | 0.022s |
| anchor | 0.535s | 0.521s | 0.444s | 0.016s | 0.009s | 0.017s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: off.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`, duplicate `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`, candidate `8f1070dbaa634e2d8cb9ac44936ed4114af7e399834c16c6bec31df9e1934dc0`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| tests::murmurhash32_inverse_roundtrips | 0.017s | 0.016s | 0.958 |
| tests::extended_zero_seed_low_word_equals_hash_bytes | 0.002s | 0.002s | 1.019 |
| tests::dynahash_wrappers | 0.002s | 0.002s | 1.021 |
| tests::uint32_paths_match_byte_path | 0.000s | 0.000s | 0.978 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
