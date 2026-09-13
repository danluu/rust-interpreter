# Indirect-call use during prepared qualification

Completed qualification shows additional native execution in prepared suites, as well as fresh exact selections. These counts do not predict elapsed time.

| Context | Test | Additional native instructions |
| --- | --- | ---: |
| fresh exact selection | token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 1,025,637 |
| fresh exact selection | token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 737,973 |
| one-worker prepared suite | token_phrase::tests::block_boundaries_preserve_maximal_runs_literal_gating_and_restart | 1,026,859 |
| one-worker prepared suite | token_phrase::tests::exhaustive_small_byte_semantics_match_pinned_regex | 637,211 |

Within each pair the original artifact, logical instruction count, memory peak and entropy qualification match. Fresh and prepared contexts have different instruction totals, so their difference does not prove a test-order or target-retention effect. A controlled first-target investigation would need matched fresh/prepared histories. No new guest execution or timing occurred in this read-only analysis.
