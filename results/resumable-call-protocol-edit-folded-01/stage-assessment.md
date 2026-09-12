# Combined engine: folded

All154 commands passed their expected outcomes: 18 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus corrected composition: paired complete-command wall change -1.06%; CPU -0.49%. Descriptive A/A envelopes: 1.30% wall, 1.58% CPU. These are not confidence intervals.

Versus fixed selected-suite anchor: wall -3.58%; CPU -3.60%.

Candidate/ordinary native paired wall ratio 0.940; candidate/line-tables native 1.013. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1.724s | 1.673s | 0.948s | 0.608s | 0.152s | 0.691s |
| duplicate | 1.703s | 1.669s | 0.927s | 0.595s | 0.151s | 0.689s |
| candidate | 1.694s | 1.661s | 0.920s | 0.590s | 0.151s | 0.691s |
| anchor | 1.783s | 1.723s | 0.951s | 0.597s | 0.167s | 0.740s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 1020/25. Binding 0.015s, template decoding 0.009s, cache load 0.009s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`, duplicate `8b16be8e49acbe0fd3c88ffadc9cef12282dab81b66dc3afca268d901796ea1e`, candidate `8f1070dbaa634e2d8cb9ac44936ed4114af7e399834c16c6bec31df9e1934dc0`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows | 0.673s | 0.673s | 0.999 |
| folded_literal_trie::tests::a_window_split_inside_multibyte_scalar_cannot_match_across_boundary | 0.013s | 0.013s | 1.003 |
| folded_literal_trie::tests::wide_classifier_matches_complete_scan_across_blocks_and_tail | 0.010s | 0.010s | 0.996 |
| folded_literal_trie::tests::windows_and_ascii_fold_differential_are_exact | 0.005s | 0.005s | 0.992 |
| folded_literal_trie::tests::kelvin_sigma_russian_and_duplicates_keep_original_byte_offsets | 0.005s | 0.005s | 1.008 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
