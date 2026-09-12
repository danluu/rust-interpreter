# Seeded valid-program coverage

Pause further emitter tuning after the failed address-check screen. Implement
the review's missing seeded valid-program differential coverage on main's
retained emitter, independently of the parked candidate.

Generate bounded two-function programs with mutable register reuse, random
arithmetic widths, casts, scalar memory widths, overlapping copies, diamonds,
counted loops and direct calls. Include heap and linear storage, call arguments
and results, and interpreted operations between native regions. Values and
memory feed the returned checksum; compare every successful profiled PC count
with the interpreter reference. Preserve exact budgets and memory peaks across
persistent-register choices, code-cap declines and profiled/unprofiled modes.

Use a fixed reproducible default seed range, with an explicitly bounded seed
and case-count override for further campaigns. On mismatch save the seed,
program bytes, arguments, runtime settings and expected/actual outcomes to a
new failure directory; never overwrite an existing reproducer. These are engine
correctness tests, not claims about Rust frontend coverage or latency.

Main starts with360tests. Add two integration tests, require362per profile.
Host qualification floor: 4 GiB, using the existing populated host cache,
two workers and locked offline dependencies. Keep real-project storage floors
and all parked performance decisions unchanged.
