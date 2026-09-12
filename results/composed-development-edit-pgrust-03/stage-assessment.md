# Combined engine: pgrust

All132 commands passed their expected outcomes: 4 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Median paired complete-command wall change +0.82%; CPU +1.26%. Descriptive A/A envelopes: 1.16% wall, 1.37% CPU. These are not confidence intervals.

Candidate/ordinary native paired wall ratio 0.936; candidate/line-tables native 0.939. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.557s | 0.541s | 0.462s | 0.017s | 0.009s | 0.017s |
| duplicate | 0.552s | 0.539s | 0.460s | 0.017s | 0.009s | 0.017s |
| candidate | 0.562s | 0.549s | 0.461s | 0.017s | 0.009s | 0.023s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: off.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`, duplicate `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`, candidate `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| tests::murmurhash32_inverse_roundtrips | 0.012s | 0.017s | 1.442 |
| tests::extended_zero_seed_low_word_equals_hash_bytes | 0.002s | 0.002s | 1.156 |
| tests::dynahash_wrappers | 0.002s | 0.002s | 1.184 |
| tests::uint32_paths_match_byte_path | 0.000s | 0.000s | 1.116 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
