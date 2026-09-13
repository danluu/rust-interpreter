# Combined engine: pgrust

All154 commands passed their expected outcomes: 4 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus wide-operation baseline: paired complete-command wall change +0.42%; CPU -0.00%. Descriptive A/A envelopes: 4.10% wall, 3.93% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 1.0452/1.0393. These are not statistical bounds.

Versus fixed selected-suite anchor: wall +0.09%; CPU -0.00%.

Candidate/ordinary native paired wall ratio 0.874; candidate/line-tables native 0.903. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.539s | 0.526s | 0.446s | 0.016s | 0.009s | 0.022s |
| duplicate | 0.542s | 0.528s | 0.446s | 0.016s | 0.009s | 0.022s |
| candidate | 0.540s | 0.527s | 0.445s | 0.016s | 0.009s | 0.022s |
| anchor | 0.539s | 0.528s | 0.449s | 0.016s | 0.009s | 0.017s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: off.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `7cc4b8989ebefb19c153c33f384a200af392ff228d9c84ab4a4fdc17d7c0891a`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| tests::murmurhash32_inverse_roundtrips | 0.016s | 0.016s | 0.996 |
| tests::extended_zero_seed_low_word_equals_hash_bytes | 0.002s | 0.002s | 0.998 |
| tests::dynahash_wrappers | 0.002s | 0.002s | 0.993 |
| tests::uint32_paths_match_byte_path | 0.000s | 0.000s | 1.010 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
