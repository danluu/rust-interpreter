# Eighteen isolated folded-trie tests benefit from shared code preparation

All 32 commands pass: 21 primary commands, seven Cargo checks and four
restored-source rebuilds. Eighteen original tests run once per suite. Native,
fresh JIT and prepared JIT agree on all test outcomes, including the wrong edit.
Tests remain unchanged, source restoration is verified, and all 14 primary plus
two restored custom artifacts match across modes.

| Five edited commands | Median complete wall time |
| --- | ---: |
| Native build + eighteen separate test processes | 1.845 s |
| Export + fresh JIT per test | 2.042 s |
| Export + shared prepared JIT | 1.821 s |

Median paired prepared/fresh ratios are 0.8916 wall and 0.8941 CPU. This single
cycle gives a descriptive 10.84% wall reduction across five distinct edits;
a repeated confirmation is still required for a stronger performance claim.
The comparison concerns isolated tests, not the existing shared-state batch.

Median custom execution falls from 1.049 to 0.850 s. Preparation falls from
61.8 to 3.6 ms, and new compilation during the eighteen tests falls from 180.7
to 42.4 ms. Cargo/export takes 0.918 and 0.909 s. Native takes 1.109 s to build
and 0.690 s across its eighteen test processes. These are separate nested
medians, not additive components of the complete-command median.

Cold commands are 9.315 s native, 7.275 s fresh and 7.196 s prepared, in fixed
native/fresh/prepared order with fresh per-mode targets and prepared tools/std
metadata. They do not constitute a balanced cold comparison.

Together with pgrust and token, this supports retaining the optional prepared
API for isolated test execution. Pgrust saves too little setup to change total
latency; token still spends most time executing generated code. Extend
correctness coverage to Ruff and Nushell before automatic suite discovery or
broader test-harness semantics. Existing ordinary-batch behavior stays available.

[Protocol](../../benchmarks/experiments/prepared-jit/WORKFLOWS.md),
[measurement](isolated-assessment.json), [verification](verification.json).
