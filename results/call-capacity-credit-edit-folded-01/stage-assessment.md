# Combined engine: folded

All154 commands passed their expected outcomes: 18 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Versus integrated baseline: paired complete-command wall change -0.56%; CPU -0.45%. Descriptive A/A envelopes: 3.27% wall, 3.35% CPU. These are not confidence intervals.

Versus fixed selected-suite anchor: wall -4.72%; CPU -4.10%.

Candidate/ordinary native paired wall ratio 0.979; candidate/line-tables native 1.009. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1.693s | 1.733s | 0.873s | 0.549s | 0.149s | 0.726s |
| duplicate | 1.659s | 1.699s | 0.857s | 0.539s | 0.144s | 0.712s |
| candidate | 1.664s | 1.704s | 0.864s | 0.538s | 0.150s | 0.722s |
| anchor | 1.766s | 1.797s | 0.911s | 0.537s | 0.171s | 0.781s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 1020/25. Binding 0.016s, template decoding 0.009s, cache load 0.009s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, duplicate `49746a2218dbfdccacac0031f47e7a13b0440489c226979ff3374f6f899e09f9`, candidate `2ad48ea7fd0d0c8a5d32e220b9c3997684d9952f13b8acd348fc59c3a6d026c3`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows | 0.708s | 0.702s | 0.997 |
| folded_literal_trie::tests::a_window_split_inside_multibyte_scalar_cannot_match_across_boundary | 0.013s | 0.013s | 1.011 |
| folded_literal_trie::tests::wide_classifier_matches_complete_scan_across_blocks_and_tail | 0.011s | 0.010s | 0.982 |
| folded_literal_trie::tests::windows_and_ascii_fold_differential_are_exact | 0.006s | 0.005s | 0.990 |
| folded_literal_trie::tests::kelvin_sigma_russian_and_duplicates_keep_original_byte_offsets | 0.005s | 0.005s | 0.988 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
