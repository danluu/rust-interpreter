# Combined engine: pgrust

All154 commands passed their expected outcomes: 4 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus wide-operation baseline: paired complete-command wall change -5.47%; CPU -4.73%. Descriptive A/A envelopes: 1.55% wall, 1.58% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 0.9622/0.9700. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -5.33%; CPU -4.57%.

Candidate/ordinary native paired wall ratio 0.890; candidate/line-tables native 0.820. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.544s | 0.529s | 0.448s | 0.016s | 0.009s | 0.022s |
| duplicate | 0.537s | 0.525s | 0.445s | 0.016s | 0.009s | 0.021s |
| candidate | 0.514s | 0.504s | 0.450s | 0.016s | 0.009s | 0.022s |
| anchor | 0.542s | 0.525s | 0.448s | 0.016s | 0.009s | 0.017s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: off.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`. Every edited candidate lookup is a validated hit. The composition changes both the VM and launcher lookup versus the wide control.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `f0af2e3e4c1093fd0e7bb5a5a53dd8e72b305d7e1536ea9c4b999ba2acaa965a`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| tests::murmurhash32_inverse_roundtrips | 0.016s | 0.017s | 1.039 |
| tests::extended_zero_seed_low_word_equals_hash_bytes | 0.002s | 0.002s | 0.995 |
| tests::dynahash_wrappers | 0.002s | 0.002s | 0.937 |
| tests::uint32_paths_match_byte_path | 0.000s | 0.000s | 0.979 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
