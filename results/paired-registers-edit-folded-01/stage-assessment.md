# Combined engine: folded

All154 commands passed their expected outcomes: 18 original tests, fifteen valid edited pairs, fifteen A/A pairs, wrong edits and compiled restoration.

Predeclared performance gate **passes**. Versus wide-operation baseline: paired complete-command wall change -0.41%; CPU -0.05%. Descriptive A/A envelopes: 3.85% wall, 3.32% CPU. These are not confidence intervals.

Wall/CPU ratios with the prospective engineering noise margin: 1.0344/1.0326. These are not statistical bounds.

Versus fixed selected-suite anchor: wall -2.15%; CPU -3.09%.

Candidate/ordinary native paired wall ratio 0.946; candidate/line-tables native 0.959. Native uses default libtest concurrency; every mode uses two Cargo workers.

| Custom mode | Whole command | CPU | Cargo | Frontend | Lowering | VM execution stage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 1.772s | 1.685s | 1.001s | 0.641s | 0.155s | 0.693s |
| duplicate | 1.794s | 1.705s | 0.995s | 0.645s | 0.159s | 0.692s |
| candidate | 1.772s | 1.687s | 1.003s | 0.647s | 0.158s | 0.688s |
| anchor | 1.817s | 1.707s | 0.997s | 0.642s | 0.171s | 0.741s |

Nested measured scopes; separate medians need not add. Native suite output is rounded; residual includes Cargo and process overhead.

Cache mode: reuse.
Median reused/lowered functions: 1020/25. Binding 0.017s, template decoding 0.010s, cache load 0.010s. These costs are nested within export; they are not additional whole-command time.

The initial fresh-cache commands are single observations, excluded from edited-pair medians. Their times and both native stage splits are retained in `stage-assessment.json`.

Tool keys: baseline `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, duplicate `f8713aaab6a02e2eefa7d68b882e4548877de5438c01cbbdc66d180036a89aa8`, candidate `7cc4b8989ebefb19c153c33f384a200af392ff228d9c84ab4a4fdc17d7c0891a`, anchor `fe9dcae0c86c6df0b6ac629034bab3a291e15e5315f9bfc87f5da9cbb4d0fe6e`.

Broader adoption still requires the other predeclared comparisons and held-outs.

Largest selected test durations:

| Test | Baseline median | Candidate median | Paired ratio |
| --- | ---: | ---: | ---: |
| folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows | 0.673s | 0.669s | 1.001 |
| folded_literal_trie::tests::a_window_split_inside_multibyte_scalar_cannot_match_across_boundary | 0.013s | 0.013s | 1.002 |
| folded_literal_trie::tests::wide_classifier_matches_complete_scan_across_blocks_and_tail | 0.010s | 0.010s | 0.982 |
| folded_literal_trie::tests::windows_and_ascii_fold_differential_are_exact | 0.005s | 0.005s | 0.972 |
| folded_literal_trie::tests::kelvin_sigma_russian_and_duplicates_keep_original_byte_offsets | 0.005s | 0.005s | 0.999 |

Constructor and test durations can overlap across workers. Compilation is included within test time. Worker assignment and prepared-code sharing can differ; per-test ratios are descriptive, not causal attribution. Logical bytecode counts are not hardware retired instructions.
