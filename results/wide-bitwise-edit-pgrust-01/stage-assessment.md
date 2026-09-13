# Combined engine: pgrust

All154 commands passed their expected outcomes: 4 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus integrated baseline: paired complete-command wall change -0.09%; CPU +0.13%. Descriptive A/A envelopes: 2.49% wall, 2.42% CPU. These are not confidence intervals.

Versus fixed selected-suite anchor: wall +1.24%; CPU +1.28%.

Candidate/ordinary native paired wall ratio 0.869; candidate/line-tables native 0.898. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.521s | 0.509s | 0.430s | 0.015s | 0.008s | 0.021s |
| duplicate | 0.520s | 0.509s | 0.431s | 0.015s | 0.008s | 0.021s |
| candidate | 0.524s | 0.509s | 0.432s | 0.016s | 0.008s | 0.021s |
| anchor | 0.516s | 0.503s | 0.427s | 0.015s | 0.009s | 0.017s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: off.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, duplicate `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, candidate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| tests::murmurhash32_inverse_roundtrips | 0.016s | 0.016s | 1.003 |
| tests::extended_zero_seed_low_word_equals_hash_bytes | 0.002s | 0.002s | 1.012 |
| tests::dynahash_wrappers | 0.002s | 0.002s | 0.993 |
| tests::uint32_paths_match_byte_path | 0.000s | 0.000s | 1.002 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
