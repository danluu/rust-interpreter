# Park the native path candidate

All 40 complete commands preserve the 12 original tests, deliberate wrong-edit
failures, five valid source edits, candidate/control artifact identity and source
restoration. The performance gate fails.

| Paired valid-edit measure | Result |
| --- | ---: |
| Candidate / adopted wall | 0.984509 |
| Candidate / adopted CPU | 1.001640 |
| Maximum individual wall A/A deviation | 2.5402% |
| Maximum individual CPU A/A deviation | 1.1868% |
| Wall ratio plus envelope | 1.009911 |
| Candidate / ordinary native wall | 1.600572 |

The 1.55% wall difference falls within observed A/A variation, and CPU increases
0.16%. These observations do not establish a useful improvement. Preserve
candidate `69005a37` on its experimental branch; do not start larger comparisons
or repeat it unchanged. Main retains adopted runtime `df4006e0`.

The descriptive paired execution-stage difference is +4.62 ms. Cargo differs by
-52.91 ms despite byte-identical compiler/exporter/wrapper components. Nested
stages and overlapping test durations cannot be added or treated as causal
attribution. Moving more calls into scalar native bodies did not establish an
end-to-end gain. The next diagnostic should compare the actual instruction work
of the new guarded bodies with their adopted counterparts before selecting a
different implementation.

Closure verifies 1,670 evidence files and 56 retained artifacts. The strict
checks and original profiles remain valid correctness evidence, not performance
evidence. See [summary](summary.json), [stage observations](stage-observations.json)
and [closure](closure.json).
