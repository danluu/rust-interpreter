# Private-store primary fails the performance gate

All 40 complete commands preserve the original assertions, deliberately wrong
edit, five valid edits and source restoration. Candidate, adopted baseline and
duplicate A/A arms produce identical bytecode/catalogs, enable scalar Calls and
share the same exporter/wrapper. Normal OS entropy, two workers and the 16 MiB
arena remain unchanged. The 12 original tests run in every command.

| Metric | Candidate / adopted | A/A envelope | Ratio plus envelope |
| --- | ---: | ---: | ---: |
| Complete wall | 1.000153 | 0.068269 | 1.068422 |
| Child CPU | 0.976356 | 0.035539 | 1.011895 |

The unchanged wall gate fails. Median wall establishes no gain; the 2.36% CPU
reduction remains inside variation. Park tool `494c9f013bb5`; do not repeat its
screen or launch full-project/parser histories. No broader comparisons started.
Main retains adopted `df4006e0` / VM `6ac4dd9e`.

The earlier exact profile's 16.42 million additional block scalar Calls prove
execution coverage, not latency savings. Paired execution observations are
95.2 ms lower while Cargo is 17.8 ms higher; these nested observations are
descriptive and non-additive, with no causal attribution. Inspect repeated
store checks and private slot traffic before selecting another implementation.

Closure verifies 1,670 evidence files and 56 artifacts. Minimum recorded free
space is 21,670,916,096 bytes. Protocol closure separately verifies all 194
inputs and logs. Its first closing invocation omitted the revision argument;
the successful closure binds the unchanged bytes at revision `911268cb`.
