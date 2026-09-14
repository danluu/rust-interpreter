# Read-only native Calls: primary gate failed

All 40 complete commands pass correctness: original assertions, deliberately
wrong edit, five valid edits and source restoration agree across the candidate,
adopted baseline, duplicate A/A, historical anchor and ordinary native. Candidate
and current controls produce identical bytecode and catalogs. Both current arms
enable scalar Calls. Normal OS entropy, two Cargo/prepared workers and the
16 MiB arena remain unchanged.

| Metric | Candidate / adopted | A/A envelope | Ratio plus envelope |
| --- | ---: | ---: | ---: |
| Complete command wall | 0.999836 | 0.019585 | 1.019421 |
| Child CPU | 0.999544 | 0.023276 | 1.022821 |

The 0.016% wall / 0.046% CPU changes establish no improvement. The wall gate
fails. Preserve the result and park candidate cb47107b9d64; do not repeat this
revision's screen or launch full-project/parser comparisons. The larger histories
and their compatibility checks remain unstarted. Incomplete controller drafts
are retained locally with an explicit unqualified/unstarted receipt.

Descriptive paired execution time is 40.8 ms lower and Cargo time 8.0 ms higher.
These nested observations are not additive or causal evidence. The earlier exact
profile's 7.73 million additional scalar Calls likewise proved coverage, not
speed. Next inspect the emitted read-only bodies and their preparation cost
before selecting another implementation. Keep adopted df4006e0 on main.

Closure verifies 1,670 evidence files and 56 retained artifacts, including all
source transitions, original test outcomes, tool identities and supervisor logs.
Minimum recorded free space is 22.99 GiB. No other session was controlled.
