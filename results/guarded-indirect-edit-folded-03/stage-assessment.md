# Combined engine: folded

All154 commands passed their expected outcomes: 18 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **does not pass**. Versus wide-operation baseline: paired complete-command wall change -0.59%; CPU +0.48%. Descriptive A/A envelopes: 10.39% wall, 4.06% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 1.0980/1.0454. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -2.93%; CPU -2.95%.

Candidate/ordinary native paired wall ratio 0.937; candidate/line-tables native 0.986. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1.768s | 1.682s | 0.988s | 0.640s | 0.153s | 0.692s |
| duplicate | 1.796s | 1.680s | 0.994s | 0.647s | 0.153s | 0.699s |
| candidate | 1.748s | 1.666s | 0.971s | 0.633s | 0.151s | 0.694s |
| anchor | 1.835s | 1.727s | 1.012s | 0.646s | 0.170s | 0.744s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 1020/25. Binding 0.017s, template decoding 0.010s, cache load 0.010s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `9e219e2ecb7cc05b2946f30467b9f3d0886e676355d50dcabf94740a82864c2c`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows | 0.673s | 0.675s | 1.002 |
| folded_literal_trie::tests::a_window_split_inside_multibyte_scalar_cannot_match_across_boundary | 0.013s | 0.013s | 0.999 |
| folded_literal_trie::tests::wide_classifier_matches_complete_scan_across_blocks_and_tail | 0.010s | 0.010s | 1.013 |
| folded_literal_trie::tests::windows_and_ascii_fold_differential_are_exact | 0.005s | 0.005s | 0.993 |
| folded_literal_trie::tests::kelvin_sigma_russian_and_duplicates_keep_original_byte_offsets | 0.005s | 0.005s | 1.053 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
