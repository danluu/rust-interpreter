# Guarded indirect-call mechanism check

All three current original tests pass with the same per-PC logical instruction counts, peak memory and recorded entropy as the completed wide-operation controls. No JIT compilation declines occurred.

| Test | Baseline interpreted operations | Candidate interpreted operations | Baseline JIT entries | Candidate JIT entries |
| --- | ---: | ---: | ---: | ---: |
| token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 1,932,198 | 906,274 | 1,932,198 | 906,274 |
| token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 2,417,740 | 1,679,751 | 2,417,740 | 1,679,751 |
| folded_literal_trie::tests::common_offset_prefilter_matches_scalar_reference_on_all_short_byte_strings_and_windows | 75,127 | 75,099 | 75,127 | 75,099 |

These are instrumented logical counts. They establish mechanism use, not elapsed-time improvement. The full changed-source comparison remains required; all original tests and controls stay in its selection.
