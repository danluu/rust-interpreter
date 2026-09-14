# Copy-to-Copy scratch availability is measurable but limited

All 12 focused controls pass. Both saved scalar captures reconstruct exactly:
1,050/1,245 ordinary functions and 60/69 scalar bodies, with identical words,
operation spans, assertions and resumes. No guest execution or executable
publication occurs. The closure verifies the frozen sources and retained data.

| Eight-byte Copy opportunity | Token block | Exhaustive token |
|---|---:|---:|
| Static Copy sites with an available x9 value | 2,930 | 3,461 |
| Samples in those complete Copy spans | 48 | 30 |
| Samples at their actual data-load instructions | 45 | 29 |
| All generated self samples | 1,814 | 1,480 |

Each eligible site has exactly one load word. Availability is queried after all
original address handling, immediately before that load. The earlier actual
instructions still run in this observer, including loads that reset its scratch
facts; it does not project the longer availability that a future substitution
might create. Exact local ranges, overlapping writes, x9 clobbers and all control
transfers retain their original conservative invalidation.

This identifies a real additional case beyond the earlier Load-only census,
with modest observed coverage: 2.48%/1.96% of generated self samples. These are
partial perturbed windows, not whole-command fractions or predicted gains.
Do not launch a standalone Copy-only timing screen on these counts. Inspect the
same captures' existing Load opportunities, then consider one bounded shared
scratch-value implementation for both operations. It must query after address
handling, retain stores, zero high halves, budgets, fault paths and profiles,
and pass native/interpreter differential tests before the original edited-source
primary gate. No runtime adoption follows from this census.
