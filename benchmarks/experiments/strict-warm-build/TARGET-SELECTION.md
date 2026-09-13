# Development target review, 2026-09-13

This is a response to the user's target-selection question, not a replacement
of the existing latency protocol or a new benchmark result. No new application
benchmark was run for this review. No sealed holdout source was inspected.

Nushell remains a useful integration stress case, but the selected
`nu-protocol` test workflow requires native host compilation through
`nu-test-support` -> `nu-cmd-extra` -> its build dependency on `nu-protocol`.
The build script imports the shared `HtmlTheme` definition and its `IntoValue`
derive. Interpreter execution improvements cannot remove that required work.

The often-quoted 3.610094 seconds is the whole instrumented host compiler
invocation, not LLVM-only time or a fixed latency floor. Its recorded LLVM
passes have 1.121397 seconds self time and object emission 0.622037 seconds;
threads overlap. The other diagnostic edit recorded 1.799660 seconds for the
host invocation. Neither profile is an uninstrumented performance comparison.
[Self-profile evidence](../../../results/strict-warm-self-profile-02/assessment.md)
and [earlier phase profile](../../../results/strict-warm-profile-01/assessment.md).

Ruff is the strongest immediately evidenced alternative in the reviewed
development corpus: a historical five-edit workflow took a median 5.603 seconds
natively and 2.893 seconds through the candidate interpreter. This runs six
existing registry tests, with matched per-state selections; it is not the whole
linter suite or a current-tool result. A separate three-edit diagnostic showed
1.007839 seconds median macro-expansion time, identifying frontend work worth
investigating rather than a demonstrated removable budget.
[Edited workflow](../../../results/paired-local-memory-forwarding-corpus-ruff-01/summary.md)
and [frontend profile](../../../results/frontend-profile-ruff-01/summary.md).

Oxc's `oxc_linter` is a prospective new development candidate. Its inspected
manifest has no build dependencies, while `oxc_macros` depends on general macro
utilities rather than the linter. This suggests a cleaner route for ordinary
rule-body edits than Nushell's observed host back-edge. It does not establish
the complete Cargo graph, interpreter compatibility, warm latency or achievable
speedup. No Oxc run was found in the checked-in benchmark/report search. The
next decision would require a pinned ordinary-build profile and unchanged
existing rule tests before performance-driven implementation.
[Linter manifest](https://github.com/oxc-project/oxc/blob/main/crates/oxc_linter/Cargo.toml)
and [macro manifest](https://github.com/oxc-project/oxc/blob/main/crates/oxc_macros/Cargo.toml)
were inspected on 2026-09-13; these links are moving branches, not benchmark pins.

Recommendation: use Ruff to guide the next measured frontend improvements,
evaluate Oxc as an additional development target, and retain Nushell as a
regression/stress case. Neither alternative is a demonstrated sub-0.5-second
large-project result. New development targets must remain separate from the
frozen holdout pool.
