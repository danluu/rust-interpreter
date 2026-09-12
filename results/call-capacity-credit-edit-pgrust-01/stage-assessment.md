# Combined engine: pgrust

All154 commands passed their expected outcomes: 4 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus integrated baseline: paired complete-command wall change -0.09%; CPU +0.01%. Descriptive A/A envelopes: 2.35% wall, 2.35% CPU. These are not confidence intervals.

Versus fixed selected-suite anchor: wall +0.53%; CPU +0.68%.

Candidate/ordinary native paired wall ratio 0.942; candidate/line-tables native 0.924. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.534s | 0.522s | 0.442s | 0.016s | 0.008s | 0.021s |
| duplicate | 0.533s | 0.522s | 0.440s | 0.016s | 0.009s | 0.021s |
| candidate | 0.532s | 0.520s | 0.439s | 0.016s | 0.009s | 0.021s |
| anchor | 0.528s | 0.514s | 0.438s | 0.016s | 0.009s | 0.017s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: off.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, duplicate `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, candidate `2ad48ea7fd0d0c8a5d32e220b9c3997684d9952f13b8acd348fc59c3a6d026c3`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| tests::murmurhash32_inverse_roundtrips | 0.016s | 0.016s | 0.992 |
| tests::extended_zero_seed_low_word_equals_hash_bytes | 0.002s | 0.002s | 0.989 |
| tests::dynahash_wrappers | 0.002s | 0.002s | 0.970 |
| tests::uint32_paths_match_byte_path | 0.000s | 0.000s | 0.988 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
