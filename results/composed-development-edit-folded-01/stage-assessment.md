# Combined engine: folded

All132 commands passed their expected outcomes: 18 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Median paired complete-command wall change -4.25%; CPU -3.30%. Descriptive A/A envelopes: 3.84% wall, 2.47% CPU. These are not confidence intervals.

Candidate/ordinary native paired wall ratio 0.947; candidate/line-tables native 0.997. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1.910s | 1.838s | 1.067s | 0.690s | 0.181s | 0.772s |
| duplicate | 1.957s | 1.859s | 1.065s | 0.689s | 0.180s | 0.783s |
| candidate | 1.833s | 1.784s | 1.025s | 0.667s | 0.165s | 0.706s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 1020/25. Binding 0.017s, template decoding 0.010s, cache load 0.010s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`, duplicate `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`, candidate `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows | 0.756s | 0.687s | 0.910 |
| folded_literal_trie::tests::a_window_split_inside_multibyte_scalar_cannot_match_across_boundary | 0.012s | 0.014s | 1.182 |
| folded_literal_trie::tests::wide_classifier_matches_complete_scan_across_blocks_and_tail | 0.009s | 0.011s | 1.188 |
| folded_literal_trie::tests::windows_and_ascii_fold_differential_are_exact | 0.005s | 0.006s | 1.124 |
| folded_literal_trie::tests::kelvin_sigma_russian_and_duplicates_keep_original_byte_offsets | 0.005s | 0.005s | 1.139 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
