# Combined engine: folded

All154 commands passed their expected outcomes: 18 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus wide-operation baseline: paired complete-command wall change +0.16%; CPU -0.00%. Descriptive A/A envelopes: 1.30% wall, 0.90% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 1.0146/1.0089. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -3.98%; CPU -3.35%.

Candidate/ordinary native paired wall ratio 0.968; candidate/line-tables native 1.030. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1.625s | 1.656s | 0.845s | 0.528s | 0.143s | 0.693s |
| duplicate | 1.614s | 1.649s | 0.844s | 0.528s | 0.142s | 0.690s |
| candidate | 1.624s | 1.656s | 0.845s | 0.527s | 0.144s | 0.698s |
| anchor | 1.695s | 1.716s | 0.866s | 0.531s | 0.167s | 0.741s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 1020/25. Binding 0.014s, template decoding 0.009s, cache load 0.008s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `f0af2e3e4c1093fd0e7bb5a5a53dd8e72b305d7e1536ea9c4b999ba2acaa965a`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows | 0.676s | 0.681s | 1.004 |
| folded_literal_trie::tests::a_window_split_inside_multibyte_scalar_cannot_match_across_boundary | 0.013s | 0.013s | 0.997 |
| folded_literal_trie::tests::wide_classifier_matches_complete_scan_across_blocks_and_tail | 0.010s | 0.010s | 0.996 |
| folded_literal_trie::tests::windows_and_ascii_fold_differential_are_exact | 0.005s | 0.005s | 0.967 |
| folded_literal_trie::tests::kelvin_sigma_russian_and_duplicates_keep_original_byte_offsets | 0.005s | 0.005s | 1.004 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
