# Combined engine: pgrust

All154 commands passed their expected outcomes: 4 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Versus wide-operation baseline: paired complete-command wall change +0.53%; CPU +0.37%. Descriptive A/A envelopes: 1.16% wall, 1.08% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 1.0199/1.0200. These are not statistical bounds.

Versus fixed selected-suite anchor: wall +0.83%; CPU +0.92%.

Candidate/ordinary native paired wall ratio 0.921; candidate/line-tables native 0.944. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.530s | 0.517s | 0.438s | 0.016s | 0.008s | 0.022s |
| duplicate | 0.534s | 0.522s | 0.440s | 0.016s | 0.009s | 0.022s |
| candidate | 0.532s | 0.521s | 0.440s | 0.016s | 0.009s | 0.022s |
| anchor | 0.532s | 0.516s | 0.443s | 0.016s | 0.009s | 0.017s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: off.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `9e219e2ecb7cc05b2946f30467b9f3d0886e676355d50dcabf94740a82864c2c`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| tests::murmurhash32_inverse_roundtrips | 0.016s | 0.016s | 1.000 |
| tests::extended_zero_seed_low_word_equals_hash_bytes | 0.002s | 0.002s | 1.004 |
| tests::dynahash_wrappers | 0.002s | 0.002s | 0.993 |
| tests::uint32_paths_match_byte_path | 0.000s | 0.000s | 0.993 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
